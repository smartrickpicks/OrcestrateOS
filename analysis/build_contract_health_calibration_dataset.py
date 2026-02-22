"""
Build a contract health calibration dataset.

Usage:
  python -m analysis.build_contract_health_calibration_dataset

Environment:
  CONTRACT_HEALTH_CALIBRATION_SOURCE:
    - postgres     -> pull from DATABASE_URL-backed tables
    - sample_json  -> derive from examples/datasets/sample_v1.json (default)
    - csv          -> pass through an existing CSV
  CONTRACT_HEALTH_CALIBRATION_DATASET_PATH:
    Output CSV path (default: analysis/contract_health_calibration_dataset.csv)
  CONTRACT_HEALTH_SAMPLE_JSON_PATH:
    Sample JSON input for sample_json mode
  CONTRACT_HEALTH_INPUT_CSV_PATH:
    Input CSV when source=csv
  CONTRACT_HEALTH_WINDOW_DAYS:
    Optional trailing window for postgres mode (default: 365)
  CONTRACT_HEALTH_MIN_ROWS:
    Minimum output rows after deterministic synthetic expansion (default: 120)
"""

from __future__ import annotations

import csv
import json
import os
import random
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional


OUTPUT_PATH = Path(
    os.getenv(
        "CONTRACT_HEALTH_CALIBRATION_DATASET_PATH",
        "analysis/contract_health_calibration_dataset.csv",
    )
)
SOURCE = os.getenv("CONTRACT_HEALTH_CALIBRATION_SOURCE", "sample_json").strip().lower()
SAMPLE_JSON_PATH = Path(
    os.getenv("CONTRACT_HEALTH_SAMPLE_JSON_PATH", "examples/datasets/sample_v1.json")
)
INPUT_CSV_PATH = Path(
    os.getenv(
        "CONTRACT_HEALTH_INPUT_CSV_PATH",
        "analysis/contract_health_calibration_dataset.csv",
    )
)
WINDOW_DAYS = int(os.getenv("CONTRACT_HEALTH_WINDOW_DAYS", "365"))
MIN_ROWS = int(os.getenv("CONTRACT_HEALTH_MIN_ROWS", "120"))

DATASET_COLUMNS = [
    "record_id",
    "raw_score",
    "label",
    "source_system",
    "issue_type",
    "created_at",
]


@dataclass
class DatasetRow:
    record_id: str
    raw_score: float
    label: int
    source_system: str
    issue_type: str
    created_at: str

    def to_dict(self) -> Dict[str, str]:
        return {
            "record_id": self.record_id,
            "raw_score": f"{self.raw_score:.6f}",
            "label": str(self.label),
            "source_system": self.source_system,
            "issue_type": self.issue_type,
            "created_at": self.created_at,
        }


def _now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _normalize_score(value: Optional[object]) -> float:
    if value is None:
        return 1.0
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return 1.0
    if parsed > 1.0:
        parsed = parsed / 100.0
    return max(0.0, min(1.0, parsed))


def _status_is_good(status_value: str) -> bool:
    status = (status_value or "").strip().lower()
    return status in {"active", "executed", "live", "ready"}


def _issue_bucket(content_bad: bool, encoding_bad: bool) -> str:
    if content_bad and encoding_bad:
        return "both"
    if content_bad:
        return "content_mismatch"
    if encoding_bad:
        return "encoding_error"
    return "none"


def _label_is_healthy(status_value: str, content_bad: bool, encoding_bad: bool) -> int:
    return int(_status_is_good(status_value) and (not content_bad) and (not encoding_bad))


def _load_rows_from_sample_json(path: Path) -> List[DatasetRow]:
    if not path.exists():
        raise FileNotFoundError(f"Sample dataset not found: {path}")
    payload = json.loads(path.read_text(encoding="utf-8"))
    contract_results = payload.get("contract_results", [])
    issues = payload.get("issues", [])

    by_contract: Dict[str, Dict[str, bool]] = {}
    for issue in issues:
        contract_key = (issue.get("contract_key") or issue.get("file_name") or "").strip()
        if not contract_key:
            continue
        issue_type = str(issue.get("issue_type", "")).upper()
        severity = str(issue.get("severity", "")).lower()
        content_bad = issue_type in {"MISSING_REQUIRED", "PICKLIST_INVALID"} and severity in {
            "blocking",
            "blocker",
            "error",
        }
        encoding_bad = any(
            token in issue_type for token in ("MOJIBAKE", "ENCODING", "OCR", "UNREADABLE")
        )
        state = by_contract.setdefault(contract_key, {"content_bad": False, "encoding_bad": False})
        state["content_bad"] = state["content_bad"] or content_bad
        state["encoding_bad"] = state["encoding_bad"] or encoding_bad

    rows: List[DatasetRow] = []
    created_at = payload.get("created_at") or _now_iso()
    for item in contract_results:
        contract_key = (item.get("contract_key") or item.get("file_name") or "").strip()
        if not contract_key:
            continue
        status = str(item.get("status", "")).strip().lower()
        issue_count = int(item.get("issue_count", 0) or 0)
        issue_state = by_contract.get(contract_key, {"content_bad": False, "encoding_bad": False})
        content_bad = bool(issue_state["content_bad"])
        encoding_bad = bool(issue_state["encoding_bad"])

        # Deterministic proxy raw score for sample mode when true score is absent.
        base = 0.92 if status == "ready" else (0.72 if status == "needs_review" else 0.42)
        score = max(0.0, min(1.0, base - min(issue_count * 0.08, 0.55)))
        if encoding_bad:
            score = max(0.0, score - 0.15)

        rows.append(
            DatasetRow(
                record_id=contract_key,
                raw_score=round(score, 6),
                label=_label_is_healthy(status, content_bad=content_bad, encoding_bad=encoding_bad),
                source_system="sample_json",
                issue_type=_issue_bucket(content_bad=content_bad, encoding_bad=encoding_bad),
                created_at=created_at,
            )
        )
    return rows


def _load_rows_from_csv(path: Path) -> List[DatasetRow]:
    if not path.exists():
        raise FileNotFoundError(f"CSV source not found: {path}")
    rows: List[DatasetRow] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            record_id = (row.get("record_id") or "").strip()
            if not record_id:
                continue
            label = int(str(row.get("label", "0")).strip() or "0")
            source_system = (row.get("source_system") or "csv").strip()
            issue_type = (row.get("issue_type") or "none").strip()
            created_at = (row.get("created_at") or _now_iso()).strip()
            rows.append(
                DatasetRow(
                    record_id=record_id,
                    raw_score=round(_normalize_score(row.get("raw_score")), 6),
                    label=1 if label else 0,
                    source_system=source_system,
                    issue_type=issue_type,
                    created_at=created_at,
                )
            )
    return rows


def _load_rows_from_postgres(database_url: str) -> List[DatasetRow]:
    import psycopg2

    window_start = datetime.now(timezone.utc) - timedelta(days=max(1, WINDOW_DAYS))
    sql = """
    WITH encoding_issues AS (
      SELECT d.contract_id,
             MAX(CASE WHEN r.quality_flag IN ('suspect_mojibake', 'unreadable', 'missing_text_layer') THEN 1 ELSE 0 END) AS has_encoding_issue
      FROM documents d
      LEFT JOIN reader_node_cache r ON r.document_id = d.id
      WHERE d.deleted_at IS NULL
      GROUP BY d.contract_id
    ),
    correction_issues AS (
      SELECT d.contract_id,
             MAX(CASE WHEN c.status IN ('pending_verifier', 'returned_to_analyst') THEN 1 ELSE 0 END) AS has_content_issue
      FROM documents d
      LEFT JOIN corrections c ON c.document_id = d.id AND c.deleted_at IS NULL
      WHERE d.deleted_at IS NULL
      GROUP BY d.contract_id
    ),
    triage_issues AS (
      SELECT c.id AS contract_id,
             MAX(CASE
               WHEN LOWER(COALESCE(ti.issue_type, '')) LIKE '%%missing%%'
                 OR LOWER(COALESCE(ti.issue_type, '')) LIKE '%%picklist%%'
               THEN 1 ELSE 0 END) AS has_content_issue,
             MAX(CASE
               WHEN LOWER(COALESCE(ti.issue_type, '')) LIKE '%%encoding%%'
                 OR LOWER(COALESCE(ti.issue_type, '')) LIKE '%%mojibake%%'
                 OR LOWER(COALESCE(ti.issue_type, '')) LIKE '%%ocr%%'
               THEN 1 ELSE 0 END) AS has_encoding_issue
      FROM contracts c
      LEFT JOIN triage_items ti
        ON ti.batch_id = c.batch_id
       AND ti.deleted_at IS NULL
       AND ti.status IN ('open', 'in_review')
      WHERE c.deleted_at IS NULL
      GROUP BY c.id
    )
    SELECT
      c.id AS record_id,
      COALESCE(c.health_score, 100) / 100.0 AS raw_score,
      LOWER(COALESCE(c.status, 'active')) AS contract_status,
      GREATEST(COALESCE(ci.has_content_issue, 0), COALESCE(ti.has_content_issue, 0)) AS has_content_issue,
      GREATEST(COALESCE(ei.has_encoding_issue, 0), COALESCE(ti.has_encoding_issue, 0)) AS has_encoding_issue,
      c.updated_at
    FROM contracts c
    LEFT JOIN encoding_issues ei ON ei.contract_id = c.id
    LEFT JOIN correction_issues ci ON ci.contract_id = c.id
    LEFT JOIN triage_issues ti ON ti.contract_id = c.id
    WHERE c.deleted_at IS NULL
      AND c.updated_at >= %s
    ORDER BY c.id ASC
    """
    rows: List[DatasetRow] = []
    with psycopg2.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (window_start,))
            for record_id, raw_score, status, has_content, has_encoding, updated_at in cur.fetchall():
                content_bad = bool(has_content)
                encoding_bad = bool(has_encoding)
                rows.append(
                    DatasetRow(
                        record_id=str(record_id),
                        raw_score=round(_normalize_score(raw_score), 6),
                        label=_label_is_healthy(str(status), content_bad, encoding_bad),
                        source_system="postgres",
                        issue_type=_issue_bucket(content_bad, encoding_bad),
                        created_at=(
                            updated_at.replace(tzinfo=timezone.utc).isoformat()
                            if isinstance(updated_at, datetime)
                            else _now_iso()
                        ),
                    )
                )
    return rows


def _deterministic_expand(rows: List[DatasetRow], min_rows: int = MIN_ROWS) -> List[DatasetRow]:
    if len(rows) >= min_rows or not rows:
        return rows
    rng = random.Random(42)
    expanded = list(rows)
    cursor = 0
    while len(expanded) < min_rows:
        src = rows[cursor % len(rows)]
        jitter = rng.uniform(-0.04, 0.04)
        new_score = max(0.0, min(1.0, src.raw_score + jitter))
        expanded.append(
            DatasetRow(
                record_id=f"{src.record_id}__synthetic_{len(expanded):04d}",
                raw_score=round(new_score, 6),
                label=src.label,
                source_system=f"{src.source_system}+synthetic",
                issue_type=src.issue_type,
                created_at=src.created_at,
            )
        )
        cursor += 1
    return expanded


def _write_rows(rows: Iterable[DatasetRow], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=DATASET_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(row.to_dict())


def build_contract_health_calibration_dataset() -> Path:
    if SOURCE == "postgres":
        database_url = os.getenv("DATABASE_URL", "").strip()
        if not database_url:
            raise RuntimeError("DATABASE_URL is required when CONTRACT_HEALTH_CALIBRATION_SOURCE=postgres")
        rows = _load_rows_from_postgres(database_url)
    elif SOURCE == "csv":
        rows = _load_rows_from_csv(INPUT_CSV_PATH)
    else:
        rows = _load_rows_from_sample_json(SAMPLE_JSON_PATH)

    rows = sorted(rows, key=lambda row: row.record_id)
    rows = _deterministic_expand(rows, min_rows=MIN_ROWS)
    _write_rows(rows, OUTPUT_PATH)

    positives = sum(1 for row in rows if row.label == 1)
    negatives = len(rows) - positives
    print(
        f"[contract-health] dataset_built source={SOURCE} rows={len(rows)} "
        f"positive={positives} negative={negatives} path={OUTPUT_PATH}"
    )
    return OUTPUT_PATH


def main() -> None:
    build_contract_health_calibration_dataset()


if __name__ == "__main__":
    main()
