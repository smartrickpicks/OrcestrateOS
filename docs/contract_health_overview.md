# Contract Health Overview

## Where the score is computed

- Primary triage score engine (client-side):
  - `ui/viewer/index.html` -> `ContractHealthScore.computeScore(...)`
  - `ui/viewer/index.html` -> `ContractHealthScore.computeAll(...)`
- Existing persisted contract score surface (server-side pass-through):
  - `server/routes/contracts.py` (`GET /batches/{bat_id}/contracts`, `GET /contracts/{ctr_id}`)
  - `contracts.health_score` column (`server/migrations/001_core_tables.sql`)

## What the score represents

The raw contract health score is a 0-100 heuristic estimate that combines:

- Content correctness signals:
  - preflight/manual blockers and warnings
  - semantic proposal backlog and lifecycle stage penalties
  - schema/unknown-column penalties
- Encoding/ingestion quality signals:
  - OCR/mojibake-style preflight penalty paths in triage/manual items
- Operational readiness:
  - stage progression and staleness penalties

Conceptually: this is an operational trust signal for whether a contract is likely safe for downstream usage (content + encoding quality).

## Current score bands and thresholds

Current raw-score triage bands in `ContractHealthScore.BANDS`:

- `Critical`: `0-34`
- `At Risk`: `35-59`
- `Watch`: `60-84`
- `Healthy`: `85-100`

## How it is consumed today

- Analyst triage contract table:
  - rendered health chips and sorting/filtering by band in `ui/viewer/index.html`
- Contracts API:
  - contract payload includes `health_score` (legacy/raw integer field)

## New calibration layer (this change)

We added a post-hoc calibration layer without rewriting raw business rules:

- Calibration training + model selection:
  - `analysis/build_contract_health_calibration_dataset.py`
  - `analysis/contract_health_calibration.py`
- Runtime decoration for API consumers:
  - `server/contract_health_runtime.py`
  - wired into `server/routes/contracts.py`

API contract now returns:

- `health_score` (legacy/raw field, preserved)
- `raw_health_score` (normalized raw probability)
- `calibrated_health_score` (canonical calibrated probability)
- `health_band` (from configurable calibrated thresholds)
- `health_score_calibration_version`

## Known limitations

- Triage UI scoring is still computed client-side and remains raw unless UI is explicitly wired to backend calibrated fields.
- Ground-truth label coverage can be sparse in small datasets; calibration scripts include deterministic synthetic expansion for stable local experimentation.
- Content-alignment details (for example strict account/object linkage checks) are approximated from currently available schema signals unless richer Salesforce-aligned labels are provided.

