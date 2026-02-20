"""
Monitor post-hoc contract health calibration quality over recent data.

Usage:
  python -m analysis.monitor_contract_health_calibration

Environment:
  CONTRACT_HEALTH_MONITOR_WINDOW_DAYS
  CONTRACT_HEALTH_ECE_ALERT_THRESHOLD
  CONTRACT_HEALTH_MONITOR_REPORT_PATH
  CONTRACT_HEALTH_MONITOR_REBUILD_DATASET (1/0)
"""

from __future__ import annotations

import csv
import os
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Iterable, List

from analysis.build_contract_health_calibration_dataset import (
    OUTPUT_PATH as DATASET_PATH,
    build_contract_health_calibration_dataset,
)
from analysis.contract_health_calibration import (
    _brier_score,
    _expected_calibration_error,
    calibrate_contract_health_score,
)


WINDOW_DAYS = int(os.getenv("CONTRACT_HEALTH_MONITOR_WINDOW_DAYS", "30"))
ECE_ALERT_THRESHOLD = float(os.getenv("CONTRACT_HEALTH_ECE_ALERT_THRESHOLD", "0.10"))
REPORT_PATH = Path(
    os.getenv(
        "CONTRACT_HEALTH_MONITOR_REPORT_PATH",
        "analysis/contract_health_calibration_monitor.md",
    )
)
REBUILD_DATASET = os.getenv("CONTRACT_HEALTH_MONITOR_REBUILD_DATASET", "0").strip() == "1"
BINS = int(os.getenv("CONTRACT_HEALTH_ECE_BINS", "15"))


@dataclass
class MonitorRow:
    created_at: datetime
    raw_score: float
    label: int


def _parse_timestamp(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00")).astimezone(timezone.utc)
    except Exception:
        return datetime.now(timezone.utc)


def _load_rows(path: Path) -> List[MonitorRow]:
    rows: List[MonitorRow] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            try:
                raw_score = float(row.get("raw_score", "0"))
                label = int(row.get("label", "0"))
            except (TypeError, ValueError):
                continue
            rows.append(
                MonitorRow(
                    created_at=_parse_timestamp(str(row.get("created_at", ""))),
                    raw_score=max(0.0, min(1.0, raw_score)),
                    label=1 if label else 0,
                )
            )
    return rows


def _format_metrics(labels: Iterable[int], raw_scores: Iterable[float]) -> str:
    y = list(labels)
    raw = list(raw_scores)
    calibrated = [calibrate_contract_health_score(score) for score in raw]
    raw_brier = _brier_score(y, raw)
    raw_ece = _expected_calibration_error(y, raw, bins=BINS)
    calibrated_brier = _brier_score(y, calibrated)
    calibrated_ece = _expected_calibration_error(y, calibrated, bins=BINS)

    status = "OK"
    if calibrated_ece > ECE_ALERT_THRESHOLD:
        status = f"ALERT (calibrated ECE {calibrated_ece:.3f} > {ECE_ALERT_THRESHOLD:.3f})"
    elif calibrated_brier > raw_brier:
        status = "WARN (calibrated Brier worse than raw)"

    report_lines = [
        f"## Contract Health Calibration - {datetime.now(timezone.utc).date().isoformat()}",
        f"Window: last {WINDOW_DAYS} days",
        f"N = {len(y)} contracts",
        "Raw score:",
        f"  - Brier: {raw_brier:.4f}",
        f"  - ECE: {raw_ece:.4f}",
        "Calibrated score:",
        f"  - Brier: {calibrated_brier:.4f}",
        f"  - ECE: {calibrated_ece:.4f}",
        f"Status: {status}",
    ]
    return "\n".join(report_lines) + "\n"


def monitor_contract_health_calibration() -> Path:
    if REBUILD_DATASET:
        build_contract_health_calibration_dataset()
    if not DATASET_PATH.exists():
        raise FileNotFoundError(
            f"Dataset not found: {DATASET_PATH}. "
            "Run python -m analysis.build_contract_health_calibration_dataset first."
        )

    rows = _load_rows(DATASET_PATH)
    cutoff = datetime.now(timezone.utc) - timedelta(days=max(1, WINDOW_DAYS))
    rows = [row for row in rows if row.created_at >= cutoff]
    if not rows:
        raise RuntimeError(
            "No rows available in monitor window. Increase CONTRACT_HEALTH_MONITOR_WINDOW_DAYS."
        )
    labels = [row.label for row in rows]
    raw_scores = [row.raw_score for row in rows]
    report = _format_metrics(labels, raw_scores)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(report, encoding="utf-8")
    print(report.strip())
    return REPORT_PATH


def main() -> None:
    out_path = monitor_contract_health_calibration()
    print(f"[contract-health] monitor_report_written path={out_path}")


if __name__ == "__main__":
    main()

