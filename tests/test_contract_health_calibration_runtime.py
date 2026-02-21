import json
from pathlib import Path

from analysis.build_contract_health_calibration_dataset import _deterministic_expand, _load_rows_from_sample_json
from server.contract_health_runtime import (
    calibrate_contract_health_score,
    classify_contract_health_band,
    decorate_contract_health,
    reset_contract_health_runtime_cache,
)


def test_sample_dataset_has_both_labels():
    rows = _load_rows_from_sample_json(
        Path("examples/datasets/sample_v1.json")
    )
    labels = {row.label for row in rows}
    assert labels == {0, 1}


def test_deterministic_expand_is_stable():
    rows = _load_rows_from_sample_json(Path("examples/datasets/sample_v1.json"))
    expanded_a = _deterministic_expand(rows, min_rows=25)
    expanded_b = _deterministic_expand(rows, min_rows=25)
    assert [row.record_id for row in expanded_a] == [row.record_id for row in expanded_b]
    assert [row.raw_score for row in expanded_a] == [row.raw_score for row in expanded_b]


def test_runtime_decorates_contract_identity_without_model(monkeypatch):
    tmp = Path("tests/.tmp_contract_health")
    tmp.mkdir(parents=True, exist_ok=True)
    missing_model = tmp / "missing_model.json"
    bands = tmp / "bands.json"
    bands.write_text(
        json.dumps(
            {
                "version": "calibrated_v1",
                "bands": [
                    {"name": "VERY_HIGH_CONFIDENCE_HEALTHY", "min": 0.95, "max": 1.01},
                    {"name": "HEALTHY_REVIEW_SPOTCHECK", "min": 0.80, "max": 0.95},
                    {"name": "NEEDS_DETAILED_REVIEW", "min": 0.00, "max": 0.80},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CONTRACT_HEALTH_CALIBRATOR_JSON", str(missing_model))
    monkeypatch.setenv("CONTRACT_HEALTH_BANDS_CONFIG", str(bands))
    reset_contract_health_runtime_cache()

    payload = decorate_contract_health({"health_score": 82})
    assert payload["raw_health_score"] == 0.82
    assert payload["calibrated_health_score"] == 0.82
    assert payload["health_band"] == "HEALTHY_REVIEW_SPOTCHECK"


def test_runtime_platt_model(monkeypatch):
    tmp = Path("tests/.tmp_contract_health")
    tmp.mkdir(parents=True, exist_ok=True)
    model = tmp / "model.json"
    bands = tmp / "bands.json"
    model.write_text(
        json.dumps(
            {
                "version": "calibrated_v1",
                "model_type": "platt",
                "platt": {"coef": 2.0, "intercept": -1.0},
            }
        ),
        encoding="utf-8",
    )
    bands.write_text(
        json.dumps(
            {
                "version": "calibrated_v1",
                "bands": [
                    {"name": "VERY_HIGH_CONFIDENCE_HEALTHY", "min": 0.95, "max": 1.01},
                    {"name": "HEALTHY_REVIEW_SPOTCHECK", "min": 0.80, "max": 0.95},
                    {"name": "NEEDS_DETAILED_REVIEW", "min": 0.00, "max": 0.80},
                ],
            }
        ),
        encoding="utf-8",
    )
    monkeypatch.setenv("CONTRACT_HEALTH_CALIBRATOR_JSON", str(model))
    monkeypatch.setenv("CONTRACT_HEALTH_BANDS_CONFIG", str(bands))
    reset_contract_health_runtime_cache()

    calibrated = calibrate_contract_health_score(0.50)
    assert calibrated > 0.0
    assert calibrated < 1.0
    assert classify_contract_health_band(calibrated) in {
        "VERY_HIGH_CONFIDENCE_HEALTHY",
        "HEALTHY_REVIEW_SPOTCHECK",
        "NEEDS_DETAILED_REVIEW",
    }

