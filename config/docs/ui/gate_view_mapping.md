# Gate-To-View Mapping (View Contract)

> Single source of truth for gate-to-view ownership. Contracts only; no implementation.

This document maps doctrine gates from [Human-Agent-Workflow-V1.json](../specs/Human-Agent-Workflow-V1.json) to their owning views.

## Gate Ownership Table

| Gate ID | Gate Name | Owning View | Required Evidence | Failure Behavior |
|---------|-----------|-------------|-------------------|------------------|
| gate_parse | Dataset Parsed | data_source_panel | row_count, column_headers, parse_timestamp | Block navigation to triage |
| gate_preflight | Preflight Check | [patch_authoring_view](views/patch_authoring_view.md) | preflight_report, badge_summary (no fail) | Block submission |
| gate_evidence | Evidence Pack | [patch_authoring_view](views/patch_authoring_view.md) | 4-block Evidence Pack complete (Observation, Expected, Justification, Repro) | Block submission |
| gate_verifier | Verifier Decision | [verifier_review_view](views/verifier_review_view.md) | review_notes, decision_status | Patch remains Under_Review |
| gate_admin | Admin Decision | [admin_approval_view](views/admin_approval_view.md) | admin_action_log, smoke_evidence | Patch remains Verifier_Approved |

## View Responsibilities

| View | Gates Owned | Read-Only Gates |
|------|-------------|-----------------|
| Triage | None | All (navigation only) |
| Record Inspection | None | All (read-only) |
| Patch Authoring | gate_preflight, gate_evidence | None |
| Verifier Review | gate_verifier | gate_preflight, gate_evidence |
| Admin Approval | gate_admin | gate_preflight, gate_evidence, gate_verifier |
| Promotion | None (post-gate) | All gates must be passed |

## References

- [Human-Agent-Workflow-V1.json](../specs/Human-Agent-Workflow-V1.json) — Gate definitions
- [Flow-Doctrine.md](../V1/Flow-Doctrine.md) — Workflow stages
- [ui_principles.md](ui_principles.md) — Review State Transition Matrix
