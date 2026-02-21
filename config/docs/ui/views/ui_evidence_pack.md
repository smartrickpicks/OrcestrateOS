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

## V2.2 Integration

- **`system_suggested` patches** (from hinge-governed proposals): These patches are auto-created when a System Pass hinge-field proposal is routed to the patch lifecycle. They require a full Evidence Pack (same blocks as Correction type) before submission. The Observation block is pre-populated with the system proposal details.
- **`preflight_resolution` patches** (from blocker one-click): These patches are created via "Create Patch from Blocker" in Pre-Flight triage. They use a simplified evidence format: only Justification (pre-filled with blocker description) and the resolved value are required. Observation, Expected, and Repro blocks are optional.

## Related Documents

- [Record Inspection](single_row_review_view.md) — where Evidence Packs are authored
- [UI Principles](../ui_principles.md) — governing design principles
