# View: Patch Authoring (Patch Studio)

> Workbench for authoring structured intent, running preflight checks, and assembling evidence packs.

## Entry Conditions

| Condition | Required |
|-----------|----------|
| Dataset loaded | Yes |
| User authenticated | Yes (any role) |
| Minimum role | Analyst |
| Issue identified | Recommended (from Record Inspection) |

## System-Suggested and Pre-Flight Patches (v2.2)

- **`system_suggested` patches**: When a System Pass hinge-field proposal is accepted via "Route to Patch", a `system_suggested` patch artifact is auto-created in `PATCH_REQUEST_STORE` and appears in the Patch Queue. These follow the standard patch lifecycle (Draft → Submitted → Verifier Review → Admin Approval → Applied) and require a full Evidence Pack.
- **`preflight_resolution` patches**: When a Pre-Flight blocker is resolved via "Create Patch from Blocker", a `preflight_resolution` patch artifact is created. These use a simplified evidence format (Justification only required) and follow the standard patch lifecycle.

## Visible Artifacts

| Artifact | Description | Required |
|----------|-------------|----------|
| Structured Intent Form | Target Field, Condition Type, Action Type | Yes |
| Intent Preview | Rendered WHEN/THEN/BECAUSE | Yes (live update) |
| Preflight Results | Pass/Warn/Fail badges | After preflight run |
| Evidence Pack Form | Observation, Expected, Justification, Repro | Yes |
| Replay Contract | Replay Type, Steps, Expected Result | Yes (per patch type) |
| Revision History | Previous revisions if editing | If editing |

## Sub-Tabs

| Tab | Purpose |
|-----|---------|
| Draft | Structured intent authoring |
| Preflight | Validation results and badge summary |
| Evidence Pack | 4-block evidence assembly + Replay Contract |

## Allowed Actions by Role

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| Edit structured intent | Yes | Yes | Yes |
| Select target field | Yes | Yes | Yes |
| Select condition/action type | Yes | Yes | Yes |
| Use "Other" escape hatch | Yes | Yes | Yes |
| Run Preflight | Yes | Yes | Yes |
| View preflight report | Yes | Yes | Yes |
| Copy preflight report | Yes | Yes | Yes |
| Edit evidence pack | Yes | Yes | Yes |
| Submit Patch Request | Yes | Yes | Yes |
| Approve/Promote patch | No | No | No |

## Disallowed Actions

| Action | Reason |
|--------|--------|
| Submit without preflight pass | gate_preflight not satisfied |
| Submit without evidence pack | gate_evidence not satisfied |
| Submit Correction/Blacklist without replay contract | gate_replay not satisfied |
| Approve own patch | Self-approval is blocked; requires different actor |
| Skip structured intent | All fields required |

## Hard Policy Rules

1. **Submit is not approval.** Submitting a patch request creates a reviewable item with status `Submitted`. No implicit approval state is set.
2. **No self-approval.** The author of a patch cannot approve or promote their own patch at any stage (Verifier or Admin). The UI blocks this with an explicit error message.
3. **Verifier must complete test + checklist + gates before promoting.** The Verifier approval requires a 6-item review checklist to be completed.
4. **Admin is the only role that can perform final promotion.** The Promote Patch to Baseline action is restricted to Admin role. Unauthorized roles do not see the Promote button (hidden, not disabled).

## Gate Ownership

This view owns three gates (see [gate_view_mapping.md](../gate_view_mapping.md)):

| Gate | Condition | On Failure |
|------|-----------|------------|
| gate_preflight | All checks pass or warn (no fail) | Block submission, show errors |
| gate_evidence | All required blocks populated per patch type | Block submission, highlight missing |
| gate_replay | Replay contract satisfied per patch type rules | Block submission, show missing replay fields |

Gate parity: Record Inspection submit and Patch Studio submit enforce identical gate conditions via the shared `validateSubmissionGates()` function.

## Replay Contract Validation (v1.6.57)

| Patch Type | replay_type | replay_steps | replay_expected_result |
|------------|-------------|--------------|------------------------|
| Correction | Required (cannot be NA) | Required (min 5 chars) | Required (min 5 chars) |
| Blacklist | Required (cannot be NA) | Required (min 5 chars) | Required (min 5 chars) |
| RFI | Optional (may be NA) | Optional | Optional |
| preflight_resolution | Optional (may be NA) | Optional | Optional |

## Audit/Evidence Requirements

| Event | Logged | Evidence |
|-------|--------|----------|
| Preflight run | Yes | timestamp, patch_id, badge_summary |
| Submit Patch Request | Yes | timestamp, patch_id, actor, intent_rendered |

## State Transitions

| From State | To State | Action | Role |
|------------|----------|--------|------|
| Draft | Submitted | Submit Patch Request | Analyst, Verifier, Admin |
| Needs_Clarification | Submitted | Respond to Clarification | Author |

## Promotion Flow (role-locked)

| From State | To State | Action | Role |
|------------|----------|--------|------|
| Submitted | Verifier_Approved | Approve (Verifier) | Verifier only (not patch author) |
| Verifier_Approved | Admin_Approved | Approve (Admin) | Admin only (not patch author) |
| Admin_Approved | Applied | Promote Patch to Baseline | Admin only |

## Form Validation

| Field | Required | Max Length |
|-------|----------|------------|
| Target Field | Yes | - |
| Condition Type | Yes | - |
| Action Type | Yes | - |
| Other (if selected) | Yes | 500 chars |
| Observation | Yes (Correction) | 1000 chars |
| Expected | Yes (Correction) | 1000 chars |
| Justification | Yes (all types) | 1000 chars |
| Repro | Yes (Correction) | 2000 chars |
| Replay Type | Yes (Correction/Blacklist) | - |
| Replay Steps | Yes (Correction/Blacklist) | 2000 chars |
| Replay Expected Result | Yes (Correction/Blacklist) | 2000 chars |

## Related Documents

- [gate_view_mapping.md](../gate_view_mapping.md) — Gate ownership
- [single_row_review_view.md](single_row_review_view.md) — Issue identification
- [verifier_review_view.md](verifier_review_view.md) — Next stage after submit
- [analyst.md](../roles/analyst.md) — Analyst role permissions
