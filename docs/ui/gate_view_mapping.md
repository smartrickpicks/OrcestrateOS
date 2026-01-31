# OoS Gate-To-View Mapping (View Contract)

This file aps documents consolidate-level mapping between doctrine gates in Human-Agent-Workflow-V1.json and their state/evidence vews. Contracts only; no implementation.

| Gate ID | Gate Short Name | VIEW Consumer | Notes |
|-------|--------------|--------|-----------|
|gate_preflight| Preflight Check | patch_authoring_view | Preflight should be triggerable from within this view (contract only) |
`-- Ref: Human-Agent-Workflow-V1.json node = "preflight_check", gate_preflight
|gate_verifier| Verifier Review | verifier_review_view | Evidence bundle visible (requires passed preflight + Evidence Requirements) |
`-- Ref: Human-Agent-Workflow-V1.json node = "verifier_review", gate_verifier
|gate_admin| Admin Approval | admin_approval_view | Admin decision visible; export visibility when applicable |
`-- Ref: Human-Agent-Workflow-V1.json node = "admin_approval", gate_admin
|promotion/export| Promote Patch to Baseline + PR Ready | promotion_view | Admin only; baseline-mutating event; audit log required |
`-- Ref: node emits "apply_patch" at Stage 11 and "exportion" at Stage 12 (review doctrine) |

References: Human-Agent-Workflow-V1.json (gate_preflight, gate_verifier, gate_admin); docs/V1/Flow-Doctrine.md; docs/overview.md.
