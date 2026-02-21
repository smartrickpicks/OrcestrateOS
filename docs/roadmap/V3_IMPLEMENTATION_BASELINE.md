# V3 Implementation Baseline (Current Branch State)

Branch: `codex/v3-unified-workspace-handoff`
Source baseline branch: `origin/fix/preflight-contractgen-stabilization`

## Important Note
This branch is intended for V3 planning/handoff first. Stabilization items must be verified against the live branch head before implementation begins.

## Stabilization Verification Checklist (Run Before V3 Code Work)
- Confirm PTL footer action wiring:
  - Open Contract Generator
  - Save Comment Draft
  - Submit Comment
  - Submit Correction
- Confirm `createPatchRequest` includes `preflight_context`.
- Confirm Kiwi export includes `preflight_context` exactly once.
- Confirm `pftlOpenContractGenerator` seeds Contract Generator from PTL context.
- Confirm no unresolved merge markers in `ui/viewer/index.html`.
- Confirm behavior/policy checks:
  - status override policy,
  - value override evidence capture,
  - preflight seed persistence behavior.

## Intended Starting Point for Claude Planning
- First output must include an explicit stabilization verification section with findings.
- Then propose V3 feature additions and phased migration strategy.
- Preserve existing patch/audit architecture while introducing `Record Inspector V2 (Beta)` workflow.
