# View: Verifier Review

> Review surface for evaluating submitted Patch Requests, requesting clarification, and approving/rejecting.

## Recent Changes (v1.5.0)

- **Verifier Triage Integration**: Clicking a row in Verifier Triage opens the Verifier Review detail view
- **Payload Data Display**: Review fields populated from localStorage verifier queue (not sample data)
- **Back Navigation**: Returns to Verifier Triage (triage page in Reviewer mode)
- **Status Mapping**: Payload statuses (pending, needs_clarification, sent_to_admin, resolved) map to review states

## Implementation Status (v1.5.0)

| Feature | Status |
|---------|--------|
| Page layout (2-column grid) | Done |
| Structured Intent display (WHEN/THEN/BECAUSE) | Done |
| Evidence Pack display (4 blocks) | Done |
| Preflight Report badges | Done |
| Author Info section | Done |
| Revision History section | Done (stub) |
| Review Notes textarea | Done |
| Verifier Actions panel | Done |
| State transitions (Submitted → Under_Review → Approved/Rejected/Needs_Clarification) | Done |
| Audit logging (client-side) | Done |
| Clarification modal | Done |
| Role-gated navigation | Done |
| Triage row → Review detail navigation (v1.5.0) | Done |
| Payload data population from queue (v1.5.0) | Done |

**Note (v1.4.17):** Patch Replay evaluation occurs in Admin Approval, not Verifier Review. Verifiers focus on semantic review; Admins perform replay validation before promotion.

## Entry Conditions

| Condition | Required |
|-----------|----------|
| Patch in Submitted or Under_Review state | Yes |
| User authenticated | Yes |
| Minimum role | Verifier |
| gate_preflight passed | Yes (from Patch Studio) |
| gate_evidence satisfied | Yes (from Patch Studio) |

**Note:** Analysts can view their own patches in read-only mode but cannot take review actions.

## Visible Artifacts

| Artifact | Description | Required |
|----------|-------------|----------|
| Structured Intent | Rendered Observation/Expected/Justification (aliases: WHEN/THEN/BECAUSE) | Yes |
| Evidence Pack | All 4 canonical blocks (Observation, Expected, Justification, Repro) | Yes |
| Preflight Report | Badge summary from submission | Yes |
| Revision History | All revisions with diff summaries | Yes |
| Author Info | Submitting actor and timestamp | Yes |
| Review Notes | Previous reviewer notes if any | If any |

## Allowed Actions by Role

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| View intent and evidence | Own only | Yes | Yes |
| View revision history | Own only | Yes | Yes |
| Begin Review | No | Yes | Yes |
| Request Clarification | No | Yes | Yes |
| Approve (Verifier) | No | Yes | Yes |
| Reject | No | Yes | Yes |
| Add review notes | No | Yes | Yes |

## Disallowed Actions

| Action | Reason |
|--------|--------|
| Edit intent | Author must revise via clarification |
| Edit evidence pack | Author must revise via clarification |
| Admin Approve | Requires Admin role |
| Promote Patch to Baseline | Requires Admin role |
| Approve own patch | Conflict of interest |

## Gate Ownership

This view owns one gate (see [gate_view_mapping.md](../gate_view_mapping.md)):

| Gate | Condition | On Failure |
|------|-----------|------------|
| gate_verifier | Verifier decision recorded | Patch remains in Under_Review |

## REVIEW_CHECKLIST Enforcement

Before approving, the Verifier must satisfy these checklist sections (see [REVIEW_CHECKLIST.md](../../REVIEW_CHECKLIST.md)):

| Section | Check |
|---------|-------|
| Intent Clarity | Plain-English description, rule_id naming, scope boundaries |
| Schema Correctness | Canonical names, valid operators, required attributes |
| Preview Validity | Repository examples, deterministic, understandable |
| Conflict Assessment | No contradictions, consistent severity, overlaps resolved |
| Downstream Risk Awareness | Workflow impact, migration notes, interactions |
| Smoke Verification | Strict pass with evidence |

**Contract:** If any checklist item cannot be verified due to missing evidence, the Verifier MUST use "Request Clarification". Approving without complete evidence is a contract violation.

## Audit/Evidence Requirements

| Event | Logged | Evidence |
|-------|--------|----------|
| Begin Review | Yes | timestamp, patch_id, verifier_actor |
| Request Clarification | Yes | timestamp, patch_id, question_text |
| Approve (Verifier) | Yes | timestamp, patch_id, verifier_actor, checklist_confirmed |
| Reject | Yes | timestamp, patch_id, verifier_actor, rejection_reason |

## State Transitions

| From State | To State | Action | Role |
|------------|----------|--------|------|
| Submitted | Under_Review | Begin Review | Verifier, Admin |
| Under_Review | Needs_Clarification | Request Clarification | Verifier, Admin |
| Under_Review | Verifier_Approved | Approve (Verifier) | Verifier, Admin |
| Under_Review | Rejected | Reject | Verifier, Admin |

## Related Documents

- [gate_view_mapping.md](../gate_view_mapping.md) — Gate ownership
- [REVIEW_CHECKLIST.md](../../REVIEW_CHECKLIST.md) — Full checklist
- [verifier.md](../roles/verifier.md) — Verifier role permissions
- [admin_approval_view.md](admin_approval_view.md) — Next stage after verifier approval
