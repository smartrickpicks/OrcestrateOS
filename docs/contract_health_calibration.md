# Contract Health Calibration

## Objective

Keep existing raw health scoring rules, then calibrate the output so score values are interpretable probabilities:

- Raw score stays available for debugging.
- Calibrated score becomes canonical for confidence interpretation and banding.

## Label definition (`is_healthy_contract`)

`label = 1` (healthy) only when all are true:

1. Status is good:
   - active/executed/live/ready-equivalent
   - not needs-fix/data-issue/encoding-error/rejected/invalid
2. Content alignment has no material mismatch:
   - no unresolved critical content mismatch signals
   - no unresolved critical required/picklist content failures
3. No blocking encoding failure:
   - no unreadable/mojibake/missing-text-layer blocking state
   - no open critical encoding issue requiring manual remediation

`label = 0` if any of the above fail.

Notes:

- In Postgres mode we infer these conditions from available tables/flags (`contracts`, `triage_items`, `corrections`, `reader_node_cache`).
- If your environment has richer Salesforce/Hub truth fields, prefer extending the dataset builder query to use them directly.

## Runbook

1. Build calibration dataset:

```bash
python -m analysis.build_contract_health_calibration_dataset
```

2. Train/evaluate calibrators and save artifacts:

```bash
python -m analysis.contract_health_calibration
```

3. Monitor ongoing calibration quality:

```bash
python -m analysis.monitor_contract_health_calibration
```

## Model selection

The trainer fits two post-hoc calibrators on top of raw score:

- Platt scaling (logistic regression)
- Isotonic regression

Selection criteria:

1. Lower ECE (Expected Calibration Error)
2. Lower Brier score (tiebreak)

## Artifacts

- Dataset:
  - `analysis/contract_health_calibration_dataset.csv`
- Models:
  - `models/contract_health_calibrator.joblib`
  - `models/contract_health_calibrator.json`
- Evaluation:
  - `analysis/contract_health_calibration_eval.json`
- Plots:
  - `analysis/plots/reliability_raw.png`
  - `analysis/plots/reliability_calibrated.png`
  - `analysis/plots/raw_score_hist.png`
  - `analysis/plots/calibrated_score_hist.png`

## Reliability diagrams interpretation

- Ideal calibration follows the diagonal line (`predicted ~= observed`).
- If points fall below diagonal, scores are overconfident.
- If points fall above diagonal, scores are underconfident.
- Goal: calibrated curve closer to diagonal than raw.

Example interpretation:

- A calibrated score of `0.80` should mean roughly 80% of contracts with that score are actually healthy.

## Retraining guidance

Retrain when any of the following occur:

- Raw scoring logic changes materially.
- New data source mapping changes (Salesforce/Hub schema changes).
- Monitoring crosses threshold (default alert: calibrated `ECE > 0.10`).

## Runtime integration

Contracts API now includes both raw and calibrated fields:

```json
{
  "contract_id": "ctr_123",
  "health_score": 91,
  "raw_health_score": 0.91,
  "calibrated_health_score": 0.78,
  "health_band": "HEALTHY_REVIEW_SPOTCHECK",
  "health_score_calibration_version": "calibrated_v1"
}
```

Band thresholds are configurable in:

- `config/contract_health_bands.json`

## Future: LLM judge

`analysis/judge_interface.py` provides a stub hook to later audit suspicious cases:

- large disagreement between raw and calibrated scores
- qualitative explanation of likely mismatch type (content vs encoding)
- threshold tuning suggestions for future calibration updates

