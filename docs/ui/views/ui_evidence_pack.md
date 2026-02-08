# Evidence Pack — V1 Specification

## Purpose
The Evidence Pack is the structured justification artifact that accompanies every Patch Request. It provides the auditable rationale for why a semantic change is correct.

## Canonical Blocks

| Block | Alias | Required | Description |
|-------|-------|----------|-------------|
| Observation | WHEN | Yes (all types) | What situation was observed |
| Expected | THEN | Yes (Correction) | What behavior is expected |
| Justification | BECAUSE | Yes (all types) | Why this change is correct |
| Repro | — | Conditional | Steps to reproduce (required for Correction unless Override active) |

## Patch Type Rules

| Patch Type | Required Blocks | Optional | Deferred (V2) |
|------------|----------------|----------|----------------|
| Correction | Observation, Expected, Justification | Repro (unless Override) | — |
| Blacklist Flag | Justification (min 10 chars) | Field changes | Blacklist Category |
| RFI | Justification (min 10 chars) | Field changes | RFI Target |

## Gate Integration

- `gate_evidence`: Validates Evidence Pack completeness per patch type rules above
- `gate_replay`: Validates Replay Contract satisfaction (Correction and Blacklist types)
- Evidence Pack is included in XLSX export under the patch metadata

## V1 Enforcement

- Blacklist Category and RFI Target are **not enforced** in V1
- No validation rules fire for these fields
- They are placeholders for V2 routing capabilities

## Related Documents

- [Single Row Review](single_row_review_view.md) — where Evidence Packs are authored
- [UI Principles](../ui_principles.md) — governing design principles
