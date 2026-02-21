"""
Train and evaluate contract health score calibration models.

Usage:
  python -m analysis.contract_health_calibration

Expected input:
  analysis/contract_health_calibration_dataset.csv

Outputs:
  - models/contract_health_calibrator.joblib
  - models/contract_health_calibrator.json
  - analysis/contract_health_calibration_eval.json
  - analysis/plots/reliability_raw.png
  - analysis/plots/reliability_calibrated.png
  - analysis/plots/raw_score_hist.png
  - analysis/plots/calibrated_score_hist.png
"""

from __future__ import annotations

import csv
import json
import math
import os
import pickle
import random
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Sequence, Tuple

from PIL import Image, ImageDraw


DATASET_PATH = Path(
    os.getenv(
        "CONTRACT_HEALTH_CALIBRATION_DATASET_PATH",
        "analysis/contract_health_calibration_dataset.csv",
    )
)
MODEL_JOBLIB_PATH = Path(
    os.getenv("CONTRACT_HEALTH_CALIBRATOR_JOBLIB", "models/contract_health_calibrator.joblib")
)
MODEL_JSON_PATH = Path(
    os.getenv("CONTRACT_HEALTH_CALIBRATOR_JSON", "models/contract_health_calibrator.json")
)
EVAL_PATH = Path(
    os.getenv(
        "CONTRACT_HEALTH_CALIBRATION_EVAL_PATH",
        "analysis/contract_health_calibration_eval.json",
    )
)
PLOTS_DIR = Path(os.getenv("CONTRACT_HEALTH_PLOTS_DIR", "analysis/plots"))
CALIBRATION_VERSION = os.getenv("CONTRACT_HEALTH_CALIBRATION_VERSION", "calibrated_v1")
BINS = int(os.getenv("CONTRACT_HEALTH_ECE_BINS", "15"))
RANDOM_STATE = int(os.getenv("CONTRACT_HEALTH_RANDOM_STATE", "42"))


@dataclass
class EvalResult:
    brier: float
    ece: float


def _mean(values: Sequence[float]) -> float:
    if not values:
        return 0.0
    return sum(values) / float(len(values))


def _normalize_score(value: float) -> float:
    parsed = float(value)
    if parsed > 1.0:
        parsed = parsed / 100.0
    return max(0.0, min(1.0, parsed))


def _sigmoid(value: float) -> float:
    if value >= 0:
        exp_neg = math.exp(-value)
        return 1.0 / (1.0 + exp_neg)
    exp_pos = math.exp(value)
    return exp_pos / (1.0 + exp_pos)


def _load_dataset(dataset_path: Path = DATASET_PATH) -> Tuple[List[float], List[int]]:
    if not dataset_path.exists():
        raise FileNotFoundError(
            f"Calibration dataset not found: {dataset_path}. "
            "Run python -m analysis.build_contract_health_calibration_dataset first."
        )
    scores: List[float] = []
    labels: List[int] = []
    with dataset_path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            if not row.get("raw_score"):
                continue
            scores.append(_normalize_score(float(row["raw_score"])))
            labels.append(1 if int(row.get("label", "0")) else 0)
    if not scores:
        raise RuntimeError(f"No rows found in dataset: {dataset_path}")
    if len(set(labels)) < 2:
        raise RuntimeError(
            "Calibration dataset needs both positive and negative labels. "
            "Current dataset contains a single class."
        )
    return scores, labels


def _brier_score(labels: Sequence[int], probs: Sequence[float]) -> float:
    return _mean([(float(p) - float(y)) ** 2 for p, y in zip(probs, labels)])


def _expected_calibration_error(labels: Sequence[int], probs: Sequence[float], bins: int = BINS) -> float:
    bucket_totals = [0 for _ in range(bins)]
    bucket_prob_sum = [0.0 for _ in range(bins)]
    bucket_label_sum = [0.0 for _ in range(bins)]

    for y, p in zip(labels, probs):
        idx = min(bins - 1, int(max(0.0, min(0.999999, p)) * bins))
        bucket_totals[idx] += 1
        bucket_prob_sum[idx] += p
        bucket_label_sum[idx] += y

    total = float(len(labels))
    ece = 0.0
    for idx in range(bins):
        count = bucket_totals[idx]
        if count == 0:
            continue
        avg_confidence = bucket_prob_sum[idx] / count
        avg_accuracy = bucket_label_sum[idx] / count
        ece += (count / total) * abs(avg_confidence - avg_accuracy)
    return ece


def _evaluate(labels: Sequence[int], probs: Sequence[float]) -> EvalResult:
    return EvalResult(
        brier=_brier_score(labels, probs),
        ece=_expected_calibration_error(labels, probs),
    )


def _stratified_split(
    scores: Sequence[float], labels: Sequence[int], test_size: float = 0.25, seed: int = RANDOM_STATE
) -> Tuple[List[float], List[float], List[int], List[int]]:
    rng = random.Random(seed)
    idx_by_label = {0: [], 1: []}
    for idx, label in enumerate(labels):
        idx_by_label[label].append(idx)
    for label in idx_by_label:
        rng.shuffle(idx_by_label[label])

    val_idx: List[int] = []
    train_idx: List[int] = []
    for label, indexes in idx_by_label.items():
        n_val = max(1, int(round(len(indexes) * test_size)))
        n_val = min(n_val, len(indexes) - 1) if len(indexes) > 1 else 1
        val_idx.extend(indexes[:n_val])
        train_idx.extend(indexes[n_val:])

    if not train_idx or not val_idx:
        # Fallback deterministic split.
        pivot = max(1, int(len(scores) * (1.0 - test_size)))
        ordered = list(range(len(scores)))
        train_idx = ordered[:pivot]
        val_idx = ordered[pivot:]

    x_train = [scores[idx] for idx in train_idx]
    y_train = [labels[idx] for idx in train_idx]
    x_val = [scores[idx] for idx in val_idx]
    y_val = [labels[idx] for idx in val_idx]
    return x_train, x_val, y_train, y_val


def _fit_platt_scaler(
    scores: Sequence[float],
    labels: Sequence[int],
    epochs: int = 4000,
    initial_lr: float = 0.8,
    l2: float = 0.02,
) -> Dict[str, float]:
    coef = 1.0
    intercept = 0.0
    lr = initial_lr
    n = float(len(scores))

    for _ in range(epochs):
        grad_coef = 0.0
        grad_intercept = 0.0
        for x, y in zip(scores, labels):
            pred = _sigmoid((coef * x) + intercept)
            err = pred - y
            grad_coef += err * x
            grad_intercept += err
        grad_coef = (grad_coef / n) + (l2 * coef)
        grad_intercept = grad_intercept / n

        coef -= lr * grad_coef
        intercept -= lr * grad_intercept
        lr *= 0.999
    return {"coef": float(coef), "intercept": float(intercept)}


def _predict_platt(scores: Sequence[float], params: Dict[str, float]) -> List[float]:
    coef = float(params["coef"])
    intercept = float(params["intercept"])
    return [_sigmoid((coef * x) + intercept) for x in scores]


def _fit_isotonic_scaler(scores: Sequence[float], labels: Sequence[int]) -> Dict[str, List[float]]:
    points = sorted((float(x), float(y)) for x, y in zip(scores, labels))
    if not points:
        return {"x": [0.0, 1.0], "y": [0.0, 1.0]}

    blocks = [{"sum_y": y, "sum_w": 1.0, "xs": [x]} for x, y in points]

    idx = 0
    while idx < len(blocks) - 1:
        mean_a = blocks[idx]["sum_y"] / blocks[idx]["sum_w"]
        mean_b = blocks[idx + 1]["sum_y"] / blocks[idx + 1]["sum_w"]
        if mean_a > mean_b:
            blocks[idx]["sum_y"] += blocks[idx + 1]["sum_y"]
            blocks[idx]["sum_w"] += blocks[idx + 1]["sum_w"]
            blocks[idx]["xs"].extend(blocks[idx + 1]["xs"])
            del blocks[idx + 1]
            if idx > 0:
                idx -= 1
        else:
            idx += 1

    xs: List[float] = []
    ys: List[float] = []
    for block in blocks:
        xs.append(max(block["xs"]))
        ys.append(block["sum_y"] / block["sum_w"])

    # Ensure full-range interpolation anchors.
    if xs[0] > 0.0:
        xs.insert(0, 0.0)
        ys.insert(0, ys[0])
    if xs[-1] < 1.0:
        xs.append(1.0)
        ys.append(ys[-1])

    return {"x": [float(v) for v in xs], "y": [float(v) for v in ys]}


def _predict_isotonic(scores: Sequence[float], params: Dict[str, List[float]]) -> List[float]:
    x_values = [float(v) for v in params.get("x", [])]
    y_values = [float(v) for v in params.get("y", [])]
    if not x_values or not y_values or len(x_values) != len(y_values):
        return [float(v) for v in scores]

    out: List[float] = []
    for score in scores:
        score = _normalize_score(score)
        if score <= x_values[0]:
            out.append(max(0.0, min(1.0, y_values[0])))
            continue
        if score >= x_values[-1]:
            out.append(max(0.0, min(1.0, y_values[-1])))
            continue
        pushed = False
        for idx in range(1, len(x_values)):
            left_x = x_values[idx - 1]
            right_x = x_values[idx]
            if left_x <= score <= right_x:
                left_y = y_values[idx - 1]
                right_y = y_values[idx]
                if right_x == left_x:
                    out.append(max(0.0, min(1.0, right_y)))
                else:
                    t = (score - left_x) / (right_x - left_x)
                    out.append(max(0.0, min(1.0, left_y + (t * (right_y - left_y)))))
                pushed = True
                break
        if not pushed:
            out.append(max(0.0, min(1.0, score)))
    return out


def _select_best_model(platt_eval: EvalResult, isotonic_eval: EvalResult) -> str:
    platt_key = (round(platt_eval.ece, 8), round(platt_eval.brier, 8))
    iso_key = (round(isotonic_eval.ece, 8), round(isotonic_eval.brier, 8))
    return "platt" if platt_key <= iso_key else "isotonic"


def _write_json(path: Path, payload: Dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True), encoding="utf-8")


def train_contract_health_calibrator() -> Dict[str, object]:
    scores, labels = _load_dataset(DATASET_PATH)
    x_train, x_val, y_train, y_val = _stratified_split(scores, labels)

    platt_params = _fit_platt_scaler(x_train, y_train)
    platt_val_probs = _predict_platt(x_val, platt_params)
    platt_eval = _evaluate(y_val, platt_val_probs)

    iso_params = _fit_isotonic_scaler(x_train, y_train)
    iso_val_probs = _predict_isotonic(x_val, iso_params)
    isotonic_eval = _evaluate(y_val, iso_val_probs)

    best_model_name = _select_best_model(platt_eval=platt_eval, isotonic_eval=isotonic_eval)

    if best_model_name == "platt":
        selected_params = _fit_platt_scaler(scores, labels)
        calibrated_scores = _predict_platt(scores, selected_params)
        model_json = {
            "version": CALIBRATION_VERSION,
            "model_type": "platt",
            "platt": selected_params,
        }
    else:
        selected_params = _fit_isotonic_scaler(scores, labels)
        calibrated_scores = _predict_isotonic(scores, selected_params)
        model_json = {
            "version": CALIBRATION_VERSION,
            "model_type": "isotonic",
            "isotonic": selected_params,
        }

    raw_eval = _evaluate(labels, scores)
    selected_eval = _evaluate(labels, calibrated_scores)

    metrics = {
        "raw": {"brier": raw_eval.brier, "ece": raw_eval.ece},
        "platt_validation": {"brier": platt_eval.brier, "ece": platt_eval.ece},
        "isotonic_validation": {"brier": isotonic_eval.brier, "ece": isotonic_eval.ece},
        "selected_full_dataset": {"brier": selected_eval.brier, "ece": selected_eval.ece},
        "selected_model": best_model_name,
    }

    trained_at = datetime.now(timezone.utc).replace(microsecond=0).isoformat()
    model_json["trained_at"] = trained_at
    model_json["metrics"] = metrics

    MODEL_JOBLIB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with MODEL_JOBLIB_PATH.open("wb") as handle:
        pickle.dump(model_json, handle)

    _write_json(MODEL_JSON_PATH, model_json)
    _write_json(
        EVAL_PATH,
        {
            "version": CALIBRATION_VERSION,
            "trained_at": trained_at,
            "labels": labels,
            "raw_scores": [float(score) for score in scores],
            "calibrated_scores": [float(score) for score in calibrated_scores],
            "metrics": metrics,
        },
    )
    return {"model": model_json, "metrics": metrics}


def _load_model_json(path: Path = MODEL_JSON_PATH) -> Dict[str, object]:
    if not path.exists():
        return {"version": CALIBRATION_VERSION, "model_type": "identity"}
    return json.loads(path.read_text(encoding="utf-8"))


def calibrate_contract_health_score(raw_score: float) -> float:
    model_payload = _load_model_json(MODEL_JSON_PATH)
    score = _normalize_score(raw_score)
    model_type = str(model_payload.get("model_type", "identity")).lower()
    if model_type == "platt":
        return _predict_platt([score], model_payload.get("platt", {}))[0]
    if model_type == "isotonic":
        return _predict_isotonic([score], model_payload.get("isotonic", {}))[0]
    return score


def _reliability_curve_data(
    labels: Sequence[int], probs: Sequence[float], bins: int = BINS
) -> Tuple[List[float], List[float], List[int]]:
    counts = [0 for _ in range(bins)]
    conf_sums = [0.0 for _ in range(bins)]
    acc_sums = [0.0 for _ in range(bins)]
    for y, p in zip(labels, probs):
        idx = min(bins - 1, int(max(0.0, min(0.999999, p)) * bins))
        counts[idx] += 1
        conf_sums[idx] += p
        acc_sums[idx] += y
    mean_conf = []
    mean_acc = []
    out_counts = []
    for idx in range(bins):
        if counts[idx] == 0:
            continue
        mean_conf.append(conf_sums[idx] / counts[idx])
        mean_acc.append(acc_sums[idx] / counts[idx])
        out_counts.append(counts[idx])
    return mean_conf, mean_acc, out_counts


def _draw_axes(draw: ImageDraw.ImageDraw, width: int, height: int, margin: int) -> None:
    draw.rectangle((0, 0, width - 1, height - 1), outline=(220, 220, 220))
    draw.line((margin, height - margin, width - margin, height - margin), fill=(80, 80, 80), width=2)
    draw.line((margin, margin, margin, height - margin), fill=(80, 80, 80), width=2)


def _plot_to_canvas(
    path: Path,
    labels: Sequence[int],
    probs: Sequence[float],
    title_color: Tuple[int, int, int] = (21, 101, 192),
) -> None:
    width, height, margin = 680, 500, 60
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    _draw_axes(draw, width, height, margin)

    # Ideal diagonal.
    draw.line((margin, height - margin, width - margin, margin), fill=(170, 170, 170), width=2)

    x_vals, y_vals, _ = _reliability_curve_data(labels, probs, bins=BINS)
    points = []
    for x, y in zip(x_vals, y_vals):
        px = margin + int((width - (2 * margin)) * x)
        py = (height - margin) - int((height - (2 * margin)) * y)
        points.append((px, py))

    if len(points) > 1:
        draw.line(points, fill=title_color, width=3)
    for px, py in points:
        draw.ellipse((px - 4, py - 4, px + 4, py + 4), fill=title_color, outline=(255, 255, 255))

    img.save(path, format="PNG")


def _plot_hist(path: Path, probs: Sequence[float], bar_color: Tuple[int, int, int]) -> None:
    width, height, margin = 680, 500, 60
    img = Image.new("RGB", (width, height), (255, 255, 255))
    draw = ImageDraw.Draw(img)
    _draw_axes(draw, width, height, margin)

    bins = BINS
    counts = [0 for _ in range(bins)]
    for p in probs:
        idx = min(bins - 1, int(max(0.0, min(0.999999, p)) * bins))
        counts[idx] += 1
    max_count = max(counts) if counts else 1

    chart_w = width - (2 * margin)
    chart_h = height - (2 * margin)
    bar_w = chart_w / float(bins)
    for idx, count in enumerate(counts):
        left = margin + int(idx * bar_w)
        right = margin + int((idx + 1) * bar_w) - 2
        bar_h = int((count / float(max_count)) * chart_h)
        top = (height - margin) - bar_h
        draw.rectangle((left, top, right, height - margin), fill=bar_color, outline=(255, 255, 255))

    img.save(path, format="PNG")


def plot_reliability_diagrams(output_dir: str = "analysis/plots") -> None:
    if not EVAL_PATH.exists():
        raise FileNotFoundError(
            f"Calibration eval file not found: {EVAL_PATH}. "
            "Run python -m analysis.contract_health_calibration first."
        )
    eval_payload = json.loads(EVAL_PATH.read_text(encoding="utf-8"))
    labels = [int(v) for v in eval_payload["labels"]]
    raw_scores = [float(v) for v in eval_payload["raw_scores"]]
    calibrated_scores = [float(v) for v in eval_payload["calibrated_scores"]]

    out_dir = Path(output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    _plot_to_canvas(out_dir / "reliability_raw.png", labels, raw_scores, title_color=(198, 40, 40))
    _plot_to_canvas(
        out_dir / "reliability_calibrated.png",
        labels,
        calibrated_scores,
        title_color=(46, 125, 50),
    )
    _plot_hist(out_dir / "raw_score_hist.png", raw_scores, bar_color=(21, 101, 192))
    _plot_hist(
        out_dir / "calibrated_score_hist.png",
        calibrated_scores,
        bar_color=(46, 125, 50),
    )


def main() -> None:
    result = train_contract_health_calibrator()
    print(
        "[contract-health] calibration_trained "
        f"model={result['metrics']['selected_model']} "
        f"raw_ece={result['metrics']['raw']['ece']:.4f} "
        f"calibrated_ece={result['metrics']['selected_full_dataset']['ece']:.4f}"
    )
    plot_reliability_diagrams(str(PLOTS_DIR))
    print(f"[contract-health] plots_written path={PLOTS_DIR}")


if __name__ == "__main__":
    main()
