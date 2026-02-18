# View: Verifier Review

> Review surface for evaluating submitted Patch Requests, requesting clarification, and approving/rejecting.


## Recent Changes (v1.6.59)

- **Real Audit Timeline**: All verifier field actions (approve, reject, request clarification) emit real AuditTimeline events
- **Event Types**: FIELD_VERIFIED (approve), FIELD_CORRECTED (reject), REQUEST_CLARIFICATION (clarification request) persisted to IndexedDB
- **Verifier Approve**: Emits VERIFIER_APPROVED via updatePatchRequestStatus transition, persisted to AuditTimeline

## Recent Changes (v1.5.2)

- **Record Inspection Hydration Refactor**: Loads PatchRequest by `patch_request_id` first, then record by `record_id`
- **Blocking Error UI**: Shows exact storage key when PatchRequest not found
- **Debug Panel**: `?debug=1` URL param shows traceability info

## Recent Changes (v1.5.0)

- **Verifier Triage Integration**: Clicking a row in Verifier Triage opens the Verifier Review detail view
- **Payload Data Display**: Review fields populated from localStorage verifier queue (not sample data)
- **Back Navigation**: Returns to Verifier Triage (triage page in Verifier mode)
- **Status Mapping**: Payload statuses (pending, needs_clarification, sent_to_admin, resolved) map to review states

---

## Record Inspection Hydration Sequence (v1.5.2)

When opening a queue item for review, the system follows a strict lookup sequence:

### Step 1: Load PatchRequest
```
patch_request_id → PATCH_REQUEST_STORE.get("pr:{patch_request_id}")
```
- **If found**: Proceed to Step 2
- **If not found**: Show blocking error UI with storage key

### Step 2: Load Record
```
record_id → workbook.sheets[*].rows.find(r => r.record_id === record_id)
```
- Searches all contract sections for matching `record_id`
- Falls back to `_identity.record_id` if top-level missing
- Legacy fallback: `contract_key` (deprecated)

### Step 3: Bind Record Inspection Context
```javascript
srrState.currentRecordId = record_id;
srrState.currentPatchRequestId = patch_request_id;
srrState.currentPatchRequest = patchRequest;
```

### Blocking Error Behavior
If PatchRequest not found, Record Inspection displays:
- Red error banner: "PatchRequest not found"
- Storage key attempted: `pr:{patch_request_id}`
- No record data loaded (prevents stale binding)

### Read-Only Mode
When opened by Verifier/Admin:
- Field Inspector: Read-only (no edit actions)
- Patch Editor: Read-only (displays `proposed_changes`, `evidence_pack`)
- Actions available: Approve, Reject, Request Clarification

---

## Debug Panel (v1.5.2)

A collapsible debug panel is available for traceability during development and troubleshooting.

### Activation
Add `?debug=1` to the URL:
```
/ui/viewer/index.html?debug=1
```

### Displayed Fields

| Field | Description |
|-------|-------------|
| Role | Current user role (Analyst/Verifier/Admin) |
| tenant_id | Active tenant context |
| division_id | Active division context |
| dataset_id | Current dataset identifier |
| record_id | Current record identifier |
| patch_request_id | Current patch request identifier |
| Storage Keys | localStorage keys with load status |

### Load Status Indicators
- **Green checkmark**: Successfully loaded from storage
- **Red X**: Not found in storage

### Usage
- Debug panel is hidden by default (production)
- Only visible when `?debug=1` is in URL
- Does not affect application behavior

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
| Review Notes | Previous verifier notes if any | If any |

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
