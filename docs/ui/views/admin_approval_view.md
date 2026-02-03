# View: Admin Approval

> Final approval surface for Admin decisions before Promote Patch to Baseline.

## Implementation Status (v1.4.5)

| Feature | Status |
|---------|--------|
| Page layout (2-column grid) | Done |
| Structured Intent display (WHEN/THEN/BECAUSE) | Done |
| Evidence Pack display (4 blocks) | Done |
| Preflight Report badges | Done |
| Verifier Decision section | Done |
| Revision History section | Done (stub) |
| Smoke (Strict) Status indicator | Done |
| Changelog Preview | Done |
| Admin Notes textarea | Done |
| Admin Actions panel | Done |
| State transitions (Verifier_Approved → Admin_Approved/Admin_Hold → Promoted) | Done |
| Audit logging (client-side) | Done |
| Hold modal | Done |
| Role-gated navigation (admin-only) | Done |

## Entry Conditions

| Condition | Required |
|-----------|----------|
| Patch in Verifier_Approved or Admin_Hold state | Yes |
| User authenticated | Yes |
| Minimum role | Admin |
| gate_verifier passed | Yes |

**Note:** Verifiers can view this page in read-only mode but cannot take approval actions.

## Visible Artifacts

| Artifact | Description | Required |
|----------|-------------|----------|
| Structured Intent | Rendered Observation/Expected/Justification (aliases: WHEN/THEN/BECAUSE) | Yes |
| Evidence Pack | All 4 canonical blocks (Observation, Expected, Justification, Repro) | Yes |
| Preflight Report | Badge summary | Yes |
| Verifier Decision | Approval notes and timestamp | Yes |
| Revision History | All revisions with diff summaries | Yes |
| Smoke (Strict) Status | Pass/fail indicator | Yes |
| Changelog Preview | Proposed changelog entry | Yes |

## Allowed Actions by Role

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| View all artifacts | No | Read-only | Yes |
| Admin Approve | No | No | Yes |
| Admin Hold | No | No | Yes |
| Release Hold | No | No | Yes |
| Add admin notes | No | No | Yes |
| Export preview | No | No | Yes |

## Disallowed Actions

| Action | Reason |
|--------|--------|
| Edit intent or evidence | Locked after verifier approval |
| Revert to Under_Review | Use Admin Hold instead |
| Promote without smoke pass | gate_admin requires smoke evidence |
| Skip changelog | Required for promotion |

## Gate Ownership

This view owns one gate (see [gate_view_mapping.md](../gate_view_mapping.md)):

| Gate | Condition | On Failure |
|------|-----------|------------|
| gate_admin | Admin decision recorded + smoke pass | Patch remains in Verifier_Approved |

## REVIEW_CHECKLIST Enforcement

Before Admin Approve, the Admin must confirm ALL checklist sections (see [REVIEW_CHECKLIST.md](../../REVIEW_CHECKLIST.md)):

| Section | Check |
|---------|-------|
| Intent Clarity | Confirmed by Verifier |
| Schema Correctness | Confirmed by Verifier |
| Preview Validity | Confirmed by Verifier |
| Conflict Assessment | Confirmed by Verifier |
| Downstream Risk Awareness | Confirmed by Verifier |
| Smoke (Strict) Verification | **Must be currently passing** (not just at submit time) |
| Versioning and Changelog | Version increment, changelog entry present |

**Contract:** If Smoke (Strict) is not currently passing, the Admin MUST use "Admin Hold". If changelog is missing, the Admin MUST request it before approval. Promote Patch to Baseline without passing Smoke (Strict) and complete changelog is a contract violation.

## Audit/Evidence Requirements

| Event | Logged | Evidence |
|-------|--------|----------|
| Admin Approve | Yes | timestamp, patch_id, admin_actor, smoke_evidence_ref |
| Admin Hold | Yes | timestamp, patch_id, admin_actor, hold_reason |
| Release Hold | Yes | timestamp, patch_id, admin_actor |

## State Transitions

| From State | To State | Action | Role |
|------------|----------|--------|------|
| Verifier_Approved | Admin_Approved | Admin Approve | Admin |
| Verifier_Approved | Admin_Hold | Admin Hold | Admin |
| Admin_Hold | Verifier_Approved | Release Hold | Admin |
| Admin_Approved | Promoted | Promote Patch to Baseline | Admin |

## Related Documents

- [gate_view_mapping.md](../gate_view_mapping.md) — Gate ownership
- [REVIEW_CHECKLIST.md](../../REVIEW_CHECKLIST.md) — Full checklist
- [admin.md](../roles/admin.md) — Admin role permissions
- [promotion_view.md](promotion_view.md) — Next stage after admin approval
