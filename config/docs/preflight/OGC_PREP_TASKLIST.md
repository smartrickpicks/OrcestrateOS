# OGC Prep Tasklist (No Timeline)

## Guardrails
- No schema changes.
- No matching/chunking/extraction changes.
- No autonomous triggers.
- Admin-only sandbox.
- Export from cached state only.

## Tasks

1. Confirm canonical export input state
- Use only sync preflight state already rendered in UI.
- Do not merge with legacy preflight models.

2. Add/extend admin-only Prep Review modal wiring
- Present cached preflight summary and cached OGC visibility.
- Add simulator actions (`CONTINUE`, `ACCEPT_RISK`, `ESCALATE_OCR`, `CANCEL`).

3. Persist simulator action in canonical client state
- Record action and timestamp in state used for export.
- Close modal on action; no downstream trigger.

4. Add Export Prep JSON actions
- `Copy JSON` and `Download JSON`.
- Build payload from cached state only.

5. Implement deterministic payload normalization
- Stable keys, null policy, deterministic array ordering.

6. Include optional evaluation block
- If evaluation mode state exists, embed it with locked semantics.
- Do not affect submit gating.

7. Enforce admin sandbox visibility and API contract
- Non-admin hides/disables controls and shows `Admin-only sandbox.`.
- Any blocked API path returns exact v2.5 FORBIDDEN envelope contract.

8. Verify against acceptance matrix
- Validate no recompute behavior, no scope drift, no schema impact.
