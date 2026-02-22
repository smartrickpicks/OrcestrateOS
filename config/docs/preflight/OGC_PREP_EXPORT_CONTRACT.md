# OGC Prep Export Contract (Doc-Only)

## Contract
- Schema: `prep_export_v0`
- Source of truth: cached preflight state currently used by UI for the selected doc/workspace.
- Recompute policy: forbidden for export.

## Required Top-Level Keys
- `schema_version`
- `generated_at`
- `context`
- `source`
- `preflight`
- `ogc_preview`
- `operator_decisions`
- `evaluation`

## Context Rules
- `workspace_id` must reflect effective workspace scope.
- `doc_id` is real doc id or derived id (`doc_derived_<hash>`).
- Cache metadata must identify the cached snapshot used by UI (`cache_key`, cached timestamp).

## Preflight Rules
- Must mirror cached preflight values shown in UI:
  - gate fields (`doc_mode`, `recommended_gate`, `reason_codes`)
  - metrics snapshot
  - page summaries
  - persistence block (`cache_written`, `fk_bound_writes_skipped`, `skip_reason`)
- Must not be re-derived during export.

## OGC Rules
- If cached OGC exists, include it verbatim in `ogc_preview`.
- If absent, include `included=false` and empty/null blocks in stable form.
- Geometry fields (`coord_space`, `page_w`, `page_h`, `bbox`, `quads`) must be preserved if present.

## Operator Decisions Rules
- Include latest simulator decision:
  - `CONTINUE | ACCEPT_RISK | ESCALATE_OCR | CANCEL`
- Include optional notes and escalation metadata if present.
- This is simulation-only state unless existing flow explicitly persists.

## Evaluation Rules (optional block)
- Include only if evaluation mode/state exists.
- Must reflect locked metric semantics (TTT-2, E1/E2/E3, precision/coverage integers).

## Deterministic Ordering
- `anchors`: order by `(page_number, char_start, char_end, anchor_id)`.
- `chunks`: order by `(page_number, chunk_id)`.
- Stable key naming and null handling across runs.

## Existing vs Proposed (clarity)
Existing in repo:
- cached preflight UI state and preflight run/get endpoints.
Proposed for implementation phase:
- wiring export action to generate `prep_export_v0` from that cached state.
