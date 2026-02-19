# V256 SF Preflight Acceptance

Date: 2026-02-18
Branch: codex/v256-sf-preflight
Scope: Salesforce preflight completion (account-first resolution, deterministic grouping, Missing Required / Invalid Picklist / Mojibake)

## Summary
This handoff documents the Salesforce preflight completion work in Analyst triage. The focus is account-first resolution, consistent Missing Required / Invalid Picklist / Encoding/Mojibake findings, and deterministic grouped output by section/field. Changes are scoped to preflight + triage rendering/resolution paths only.

## Code Changes (High Level)
- Account-first identity extraction and grouping for preflight items.
- Deterministic ordering of grouped preflight output by section/field/reason.
- Missing Required / Invalid Picklist preflight items include account identity and stable sort.
- Triage resolution prefers rows with actual missing/invalid values (blank or invalid picklist) before contract fallback.

## Tests Added
`tests/test_sf_preflight_determinism.py`
- Account-first resolution prefers missing row for THE THEORIST.
- Company name used for grouping label when Account Name is blank (Xmart Digital PVT Ltd).
- Deterministic section/field ordering.

## Acceptance Evidence (Known Fixture)
Fixture: `examples/datasets/ostereo_demo_v1.json`

1) Account-first resolution (THE THEORIST)
- Contract: `The_Theorist_-_Increased_Payout_Threshold_Request.pdf`
- Old behavior: selects row 60 with `Billing_Zip_Postal_Code_c = L9K0C5` (not missing)
- New behavior: selects row 133 with `Billing_Zip_Postal_Code_c = N/A` (missing)

2) Account label resolution with Company Name
- Contract: `Xmart_x_Ostereo_Distribution_Agreement_(FINAL_SIGNED).pdf`
- Old grouping label resolved from a different row (Account Name), not the company
- New grouping label resolves to `Xmart Digital PVT Ltd` using Company Name

3) Deterministic grouping by section/field
- Input (shuffled):
  - Billing_Zip_Postal_Code_c / MISSING_REQUIRED
  - Account_Type_c / PICKLIST_INVALID
  - Legal_Name_c / MISSING_REQUIRED
  - (contract-wide) OCR_MOJIBAKE
- Output order now deterministic:
  1. OCR_MOJIBAKE
  2. Account_Type_c / PICKLIST_INVALID
  3. Billing_Zip_Postal_Code_c / MISSING_REQUIRED
  4. Legal_Name_c / MISSING_REQUIRED

## Smoke Command
- Attempted: `python3 scripts/preflight_calibration_runner.py`
- Result: failed due to missing `playwright` dependency (`ModuleNotFoundError: No module named 'playwright'`)

## Notes
- No verifier/admin workflows were intentionally modified.
- No generated artifacts were committed under `out/`.
