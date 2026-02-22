# Role: Admin

> Elevated role with full authority: final approval, baseline promotion, and export capabilities.

## Overview

The Admin is the highest authority role responsible for:
- All Analyst and Verifier capabilities
- Final approval after verifier review
- Promoting patches to baseline (`apply_patch` permission)
- Exporting artifacts for pull requests
- Managing holds and releasing blocked patches

## Can / Cannot

### Can Do

| Capability | Description |
|------------|-------------|
| All Analyst capabilities | Load data, triage, inspect, author patches |
| All Verifier capabilities | Review, clarify, approve/reject at verifier gate |
| Admin Approve | Final approval after Verifier_Approved |
| Admin Hold | Place patch on hold pending investigation |
| Release Hold | Move held patch back to Under_Review |
| Promote Patch to Baseline | Apply patch to semantic baseline (Stage 11) |
| Export to PR | Generate PR-ready artifacts (Stage 12) |
| Access Admin Console | Full access to all admin functions |
| View audit logs | Full audit trail visibility |

### Cannot Do

| Restriction | Reason |
|-------------|--------|
| Bypass gates | Gates must still be satisfied |
| Auto-apply without evidence | Evidence pack required |
| Override smoke test failure | Smoke must pass for promotion |

## Allowed State Transitions

Based on the Review State Transition Matrix:

| From State | To State | Action |
|------------|----------|--------|
| Draft | Submitted | Submit Patch Request |
| Submitted | Under_Review | Begin Review |
| Under_Review | Needs_Clarification | Request Clarification |
| Needs_Clarification | Submitted | Respond to Clarification |
| Under_Review | Verifier_Approved | Approve (Verifier) |
| Under_Review | Rejected | Reject |
| Verifier_Approved | Admin_Approved | Approve (Admin) |
| Verifier_Approved | Admin_Hold | Hold |
| Admin_Hold | Under_Review | Release Hold |
| Admin_Approved | Applied | Promote Patch to Baseline |
| Applied | Promoted | Export to PR |

## Gate Responsibilities

| Gate | Admin Role |
|------|------------|
| gate_parse | Can satisfy |
| gate_preflight | Can satisfy |
| gate_evidence | Can satisfy |
| gate_verifier | Can satisfy (as verifier) |
| gate_admin | Owner — must record final decision |

## View Access

| View | Access Level |
|------|-------------|
| Triage | Full access |
| Record Inspection | Full access |
| Patch Authoring (Patch Studio) | Full access |
| Verifier Review | Full access |
| Admin Approval | Full access (authoring surface) |
| Promotion | Full access (authoring surface) |
| Admin Console | Full access |

## REVIEW_CHECKLIST Requirements

Before Admin Approve, the Admin must confirm all checklist sections (see [REVIEW_CHECKLIST.md](../../REVIEW_CHECKLIST.md)):

| Section | Required for Approval |
|---------|----------------------|
| Intent Clarity | Yes |
| Schema Correctness | Yes |
| Preview Validity | Yes |
| Conflict Assessment | Yes |
| Downstream Risk Awareness | Yes |
| Smoke Verification | Yes (must be passing) |
| Versioning and Changelog | Yes |

**If evidence is missing:** The Admin must use "Admin Hold" to block the patch. Promotion without complete evidence and passing smoke test is a contract violation.

## Audit Requirements

Actions that must be logged:
- Admin Approve (timestamp, patch_id, admin_actor, notes)
- Admin Hold (timestamp, patch_id, admin_actor, hold_reason)
- Release Hold (timestamp, patch_id, admin_actor)
- Promote Patch to Baseline (timestamp, patch_id, admin_actor, baseline_version)
- Export to PR (timestamp, patch_id, admin_actor, export_path)

## Related Documents

- [ui_principles.md](../ui_principles.md) — UI principles and transition matrix
- [admin_approval_view.md](../views/admin_approval_view.md) — Admin view contract
- [promotion_view.md](../views/promotion_view.md) — Promotion view contract
- [REVIEW_CHECKLIST.md](../../REVIEW_CHECKLIST.md) — Full checklist
