import json
import math
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Optional


def _model_path() -> Path:
    return Path(
        os.getenv("CONTRACT_HEALTH_CALIBRATOR_JSON", "models/contract_health_calibrator.json")
    )


def _bands_path() -> Path:
    return Path(os.getenv("CONTRACT_HEALTH_BANDS_CONFIG", "config/contract_health_bands.json"))


def _default_version() -> str:
    return os.getenv("CONTRACT_HEALTH_CALIBRATION_VERSION", "calibrated_v1")


def _clamp_probability(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed > 1.0:
        parsed = parsed / 100.0
    return max(0.0, min(1.0, parsed))


@lru_cache(maxsize=1)
def _load_calibrator_config() -> Dict[str, Any]:
    model_path = _model_path()
    if not model_path.exists():
        return {"model_type": "identity", "version": _default_version()}
    try:
        return json.loads(model_path.read_text(encoding="utf-8"))
    except Exception:
        return {"model_type": "identity", "version": _default_version()}


@lru_cache(maxsize=1)
def _load_band_config() -> Dict[str, Any]:
    bands_path = _bands_path()
    if not bands_path.exists():
        return {
            "version": _default_version(),
            "bands": [
                {"name": "VERY_HIGH_CONFIDENCE_HEALTHY", "min": 0.95, "max": 1.01},
                {"name": "HEALTHY_REVIEW_SPOTCHECK", "min": 0.80, "max": 0.95},
                {"name": "NEEDS_DETAILED_REVIEW", "min": 0.00, "max": 0.80},
            ],
        }
    try:
        return json.loads(bands_path.read_text(encoding="utf-8"))
    except Exception:
        return {
            "version": _default_version(),
            "bands": [
                {"name": "VERY_HIGH_CONFIDENCE_HEALTHY", "min": 0.95, "max": 1.01},
                {"name": "HEALTHY_REVIEW_SPOTCHECK", "min": 0.80, "max": 0.95},
                {"name": "NEEDS_DETAILED_REVIEW", "min": 0.00, "max": 0.80},
            ],
        }


def _apply_platt(probability: float, platt_cfg: Dict[str, Any]) -> float:
    coef = float(platt_cfg.get("coef", 1.0))
    intercept = float(platt_cfg.get("intercept", 0.0))
    z = (coef * probability) + intercept
    if z >= 0:
        exp_neg = math.exp(-z)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(z)
    return exp_pos / (1.0 + exp_pos)


def _apply_isotonic(probability: float, iso_cfg: Dict[str, Any]) -> float:
    x_values = [float(v) for v in iso_cfg.get("x", [])]
    y_values = [float(v) for v in iso_cfg.get("y", [])]
    if not x_values or not y_values or len(x_values) != len(y_values):
        return probability
    if probability <= x_values[0]:
        return max(0.0, min(1.0, y_values[0]))
    if probability >= x_values[-1]:
        return max(0.0, min(1.0, y_values[-1]))
    for idx in range(1, len(x_values)):
        left_x = x_values[idx - 1]
        right_x = x_values[idx]
        if left_x <= probability <= right_x:
            left_y = y_values[idx - 1]
            right_y = y_values[idx]
            if right_x == left_x:
                return max(0.0, min(1.0, right_y))
            t = (probability - left_x) / (right_x - left_x)
            return max(0.0, min(1.0, left_y + (t * (right_y - left_y))))
    return probability


def calibrate_contract_health_score(raw_score: float) -> float:
    normalized = _clamp_probability(raw_score)
    if normalized is None:
        return 0.0
    cfg = _load_calibrator_config()
    model_type = str(cfg.get("model_type", "identity")).lower()
    if model_type == "platt":
        return _apply_platt(normalized, cfg.get("platt", {}))
    if model_type == "isotonic":
        return _apply_isotonic(normalized, cfg.get("isotonic", {}))
    return normalized


def classify_contract_health_band(score_probability: float) -> str:
    score = _clamp_probability(score_probability)
    if score is None:
        score = 0.0
    cfg = _load_band_config()
    for band in cfg.get("bands", []):
        min_v = float(band.get("min", 0.0))
        max_v = float(band.get("max", 1.0))
        name = str(band.get("name", "NEEDS_DETAILED_REVIEW"))
        if min_v <= score < max_v:
            return name
    # Max-inclusive fallback for exact 1.0 and any malformed band config.
    for band in cfg.get("bands", []):
        max_v = float(band.get("max", 1.0))
        if score <= max_v:
            return str(band.get("name", "NEEDS_DETAILED_REVIEW"))
    return "NEEDS_DETAILED_REVIEW"


def get_calibration_version() -> str:
    calibrator_cfg = _load_calibrator_config()
    if calibrator_cfg.get("version"):
        return str(calibrator_cfg["version"])
    band_cfg = _load_band_config()
    if band_cfg.get("version"):
        return str(band_cfg["version"])
    return _default_version()


def decorate_contract_health(contract: Dict[str, Any]) -> Dict[str, Any]:
    raw_probability = _clamp_probability(contract.get("health_score"))
    if raw_probability is None:
        raw_probability = 1.0
    calibrated_probability = calibrate_contract_health_score(raw_probability)
    contract["raw_health_score"] = round(raw_probability, 6)
    contract["calibrated_health_score"] = round(calibrated_probability, 6)
    contract["health_band"] = classify_contract_health_band(calibrated_probability)
    contract["health_score_calibration_version"] = get_calibration_version()
    return contract


def reset_contract_health_runtime_cache() -> None:
    _load_calibrator_config.cache_clear()
    _load_band_config.cache_clear()
