# Role: Verifier

> Elevated role for reviewing patch requests, requesting clarification, and approving/rejecting at the verifier gate.

**Note:** "Reviewer" is a legacy alias for this role. Use "Verifier" in all new documentation.

## Overview

The Verifier is an elevated role responsible for:
- Reviewing patch requests submitted by Analysts
- Requesting clarification when evidence is incomplete
- Approving or rejecting patches at the verifier gate
- Ensuring REVIEW_CHECKLIST items are satisfied

## Can / Cannot

### Can Do

| Capability | Description |
|------------|-------------|
| All Analyst capabilities | Load data, triage, inspect, author patches |
| Review patches | Access verifier_review_view for any patch |
| Request Clarification | Return patch to author with questions |
| Approve (Verifier) | Advance patch to Verifier_Approved state |
| Reject | Return patch to Submitted with rejection notes |
| View revision history | See all revisions and diff summaries |

### Cannot Do

| Restriction | Reason |
|-------------|--------|
| Admin Approve | Requires Admin role |
| Promote Patch to Baseline | Requires Admin role (`apply_patch` permission) |
| Export to PR | Requires Admin role |
| Release Admin Hold | Requires Admin role |
| Access Admin Console (full) | Limited to review functions |

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

## Gate Responsibilities

| Gate | Verifier Role |
|------|---------------|
| gate_parse | Can satisfy (as operator) |
| gate_preflight | Can satisfy (as operator) |
| gate_evidence | Can satisfy (as operator) |
| gate_verifier | Owner — must record decision |
| gate_admin | Read-only — awaits admin decision |

## View Access

| View | Access Level |
|------|-------------|
| Triage | Full access |
| Record Inspection | Full access |
| Patch Authoring (Patch Studio) | Full access |
| Verifier Review | Full access (authoring surface) |
| Admin Approval | Read-only |
| Promotion | Read-only |

## REVIEW_CHECKLIST Requirements

Before approving, the Verifier must confirm these checklist sections (see [REVIEW_CHECKLIST.md](../../REVIEW_CHECKLIST.md)):

| Section | Required for Approval |
|---------|----------------------|
| Intent Clarity | Yes |
| Schema Correctness | Yes |
| Preview Validity | Yes |
| Conflict Assessment | Yes |
| Downstream Risk Awareness | Yes |
| Smoke Verification | Yes |

**If evidence is missing:** The Verifier must use "Request Clarification" to return the patch. Approval without complete evidence is a contract violation.

## Audit Requirements

Actions that must be logged:
- Begin Review (timestamp, patch_id, verifier_actor)
- Request Clarification (timestamp, patch_id, question_text)
- Approve (timestamp, patch_id, verifier_actor, notes)
- Reject (timestamp, patch_id, verifier_actor, rejection_reason)

## Related Documents

- [ui_principles.md](../ui_principles.md) — UI principles and transition matrix
- [verifier_review_view.md](../views/verifier_review_view.md) — Verifier view contract
- [REVIEW_CHECKLIST.md](../../REVIEW_CHECKLIST.md) — Full checklist
