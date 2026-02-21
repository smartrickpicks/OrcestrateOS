# Nomenclature — Orchestrate OS

## Canonical Product Name
- Orchestrate OS (official name)

## Aliases (Legacy/Indexed Names)
- Kiwi
- Kiwi Semantic Control Board
- Control Board

These aliases may appear historically; treat them as references to Orchestrate OS. Use them only as searchable labels in documentation.

## UI‑Facing Replacement Rules
- Use “Preview Packet” instead of “sf_packet” in prose/UI. The term “sf_packet” may appear inside raw JSON examples or file names only.
- Use “Truth Config” for config/config_pack.base.json
- Use “Proposed Changes” for config_pack.<version>.patch.json
- Use “Reference Expected” for examples/expected_outputs/*.json
- Use “Validation Evidence” for validator output
- Use “Smoke Evidence” for strict baseline/edge logs

## Internal Term → Human Label + Tooltip
- config_pack.base.json → Truth Config: authoritative base semantics
- config_pack.patch.json → Proposed Changes: changes[] for rules
- sf_packet (JSON) → Preview Packet: deterministic preview evidence
- examples/expected_outputs → Reference Expected: comparison target for smoke
- validation report → Validation Evidence: shape/conflicts status
- smoke logs → Smoke Evidence: pass/fail of normalized diffs
- join_triplet → Identity Keys: contract_key → file_url → file_name; nulls last; no fabrication
- sf_contract_status → Record Status: READY / NEEDS_REVIEW / BLOCKED
- sf_issues → Issues: rule/check signals per record
- sf_field_actions → Field Actions: blank/format_fix proposals
- sf_change_log → Change Log: proposed changes with timestamps
- sf_meta.ruleset_version → Ruleset Version: config version used
- Record Drawer → Record Context Panel: active record context/fields/issues/actions
- Evidence Strip → Evidence Summary: pasted gate statuses (base/patch/validation/conflicts/smoke)

## Determinism Callouts
- Sorting: severity (blocking > warning > info), then contract_key, file_url, file_name (asc; nulls last)
- Diffing: normalized object keys; arrays rendered in stable order
- Source of truth: Smoke Evidence is authoritative; editor diagnostics are non‑authoritative