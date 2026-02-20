# V256 Contract Reconstruction V1 (Ostereo Pilot)

Status: Draft implementation spec  
Scope: Admin sandbox only  
Pilot legal entity: Ostereo

## Purpose
Use Contract Generator as a preflight reconstruction path for encoding-corrupted contracts, so ingestion and generation operate on the same canonical schema and audit model.

## V1 Routing Policy
1. Green:
- Normal ingestion path.
- Optional `Generate Copy` for parity export.

2. Yellow:
- Allow `Accept Risk` or `Generate Copy`.
- If `Generate Copy` is chosen, reviewer compares source snippets vs generated clauses before promotion.

3. Red:
- Block `Accept Risk`.
- Require `Generate Copy` flow.
- Contract remains reconstruction-driven until required fields and review are complete.

## Preflight UX Changes (V1)
1. Replace OCR escalation CTA with `Generate Copy` in:
- Document preflight gate panel
- Preflight simulator modal
- Mojibake gate banner
- Preflight Test Lab footer action

2. Keep `Accept Risk` for yellow only.

3. `Generate Copy` behavior:
- Persist preflight action as `generate_copy` via `/api/preflight/action`
- Open Contract Generator page
- Attempt to seed current sheet/row context from SRR state
- Auto-run generator when context can be resolved

## Data and Governance Behavior
1. Canonical record remains JSON-first.
2. Generated markdown/PDF are exports, not source of truth.
3. Reconstruction action must remain auditable (`action_taken`, actor, timestamp).
4. Existing preflight gating logic now treats `generate_copy` as valid resolution path for yellow/red.

## Clause Safety Policy (ROVO-aligned, pilot defaults)
1. High-risk clause families require human review if reconstructed:
- Liability/indemnity
- Governing law/disputes
- IP ownership/license
- Term/termination
- Financial obligations

2. If high-risk text is unreadable, reconstruction is allowed only as draft/annotation-layer output pending reviewer approval.

3. No silent entity fallback:
- If Ostereo template is missing, require explicit reviewer note for fallback usage.

## Acceptance Criteria
1. Yellow preflight shows `Generate Copy` and allows progression when selected.
2. Red preflight blocks `Accept Risk` and requires `Generate Copy`.
3. Clicking `Generate Copy` opens Contract Generator and attempts to seed active record.
4. `/api/preflight/action` accepts `generate_copy`.
5. No regressions to existing `accept_risk` behavior in yellow.
6. Existing legacy `escalate_ocr` payloads remain tolerated for backward compatibility.

## Out of Scope (V1)
1. Full template-pack authoring UI.
2. Entity-level clause diff/merge workflows.
3. Production enablement (sandbox only in V1).

