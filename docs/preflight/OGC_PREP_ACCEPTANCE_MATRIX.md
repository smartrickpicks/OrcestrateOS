# OGC Prep Acceptance Matrix

## A. Snapshot Correctness
Pass:
- Export equals currently cached preflight/OGC snapshot used in UI.
Fail:
- Export triggers recompute or diverges from displayed cached result.

## B. Toggling Behavior
Pass:
- Visibility toggles do not trigger preflight/OGC recomputation.
Fail:
- Any toggle causes new engine run.

## C. Simulation Action Behavior
Pass:
- Action selection updates canonical state and closes modal.
- No downstream job/trigger starts.
Fail:
- Action triggers autonomous pipeline behavior.

## D. Submit Gating Isolation
Pass:
- Patch submit gating remains preflight-only as previously locked.
Fail:
- Evaluation/prep simulator state blocks/allows submit.

## E. Schema and Logic Isolation
Pass:
- No DB schema changes.
- No extraction/chunking/matching logic change.
Fail:
- Any migration or engine logic change.

## F. Admin Sandbox
Pass:
- Non-admin cannot run/export and sees `Admin-only sandbox.`.
- Blocked API paths return `FORBIDDEN` with message `Preflight is in admin sandbox mode.`.
Fail:
- Non-admin can trigger simulator/export flows.

## G. Export Contract Stability
Pass:
- `schema_version == "prep_export_v0"`.
- Stable keys and deterministic ordering.
- Includes context, preflight, optional OGC, operator decisions, optional evaluation.
Fail:
- Key drift, unstable ordering, or missing required blocks.

## H. Optional OGC / Optional Evaluation
Pass:
- Export valid when OGC absent and when evaluation absent.
Fail:
- Export fails if either block is missing.

## I. Valid-for-Rollup Rule
Pass:
- `valid_for_rollup=true` only when `targets_labeled >= 5`.
Fail:
- Any other rule applied.
