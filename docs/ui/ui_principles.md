# UI Principles (V1)

> Human authority governs all semantic decisions. The UI exists to surface evidence, enable decisions, and record audit trails.

## Product Identity

- **Product name**: Orchestrate OS
- **Primary surface**: Semantic Control Board
- **Logo usage**:
  - Logo is informational, not navigational
  - No homepage metaphor
  - Clicking logo does not trigger state changes
- **Logo format**: SVG (canonical, tight-cropped viewBox)
- **Asset location**: `assets/brand/orchestrate-os-logo.svg`

### Branding: Sidebar Header

| Token | Value |
|-------|-------|
| Header height | 56px |
| Logo box | 44px (max 48px) |
| Header padding | 10px 16px |
| Logo-title gap | 12px |

**SVG requirement**: viewBox must tightly bound the visible mark (no internal whitespace).

## Canonical Language Rule

All documentation, UI labels, and schemas must use canonical terms only. No synonyms or aliases are permitted. This ensures consistency across docs, UI, and data schemas. See `docs/overview.md` for the authoritative Canonical Terms list.

## Core Principles

### 1. Evidence-First Display
- Every view must show the artifacts required to make a decision
- No action button appears without visible supporting evidence
- Missing evidence forces a hold or flag state

### 2. Role-Gated Actions
- Actions are hidden (not just disabled) when the user lacks permission
- Role escalation is explicit and logged
- Degraded views show read-only content with clear "no permission" messaging
- Unauthorized actions are never rendered — hiding is always preferred over disabling

### 3. State-Driven Navigation
- Navigation reflects data state (empty → load, loaded → triage/grid)
- Gates block forward progression until conditions are met
- Backward navigation preserves context (no data loss)
- Sidebar Progress Block routes to Triage for detailed queue view

### 4. Audit by Design
- Every decision-bearing action writes to the audit log
- Timestamps use ISO 8601 format
- Actor identity is captured with role at time of action

### 5. Offline-First Rendering
- All views render from local state (no network fetch for display)
- Evidence artifacts are snapshots, not live queries
- Determinism: same state produces identical UI

### 6. Positive Friction (v1.6.57)
- Governance-critical actions require deliberate confirmation steps
- Submit gates enforce evidence completeness before allowing submission
- Review checklists must be completed before approval actions are enabled
- Self-approval is blocked — the patch author cannot approve their own patch at any stage
- Promotion requires completed verifier test, checklist, and gates before proceeding

## Review State Transition Matrix

This matrix defines the allowed state transitions for patch requests. Only the specified roles may initiate each transition.

| From State | To State | Initiating Role | Trigger Action |
|------------|----------|-----------------|----------------|
| Draft | Submitted | Analyst, Verifier, Admin | Submit Patch Request |
| Submitted | Under_Review | Verifier, Admin | Begin Review |
| Under_Review | Needs_Clarification | Verifier, Admin | Request Clarification |
| Needs_Clarification | Submitted | Analyst, Verifier, Admin | Respond to Clarification |
| Under_Review | Verifier_Approved | Verifier (not author) | Approve (Verifier) |
| Under_Review | Rejected | Verifier, Admin | Reject |
| Verifier_Approved | Admin_Approved | Admin (not author) | Approve (Admin) |
| Verifier_Approved | Admin_Hold | Admin | Hold |
| Admin_Hold | Under_Review | Admin | Release Hold |
| Admin_Approved | Applied | Admin | Promote Patch to Baseline |
| Applied | Promoted | Admin | Export to PR |

## Hard Policy: No Self-Approval (v1.6.57)

- If the current user authored the patch, they cannot approve it at any stage (Verifier or Admin).
- The UI blocks self-approval with an explicit error toast.
- Submit is not approval: submitting a patch request creates a reviewable item, not an approved one.

## Hard Policy: Role-Locked Promotion (v1.6.57)

- **Analyst role**: Submit only. Cannot approve or promote. Approval/promotion actions are hidden.
- **Verifier role**: Must complete review checklist and gates before approving. Cannot promote own patch. Cannot perform final promotion.
- **Admin role**: Final promote only. Must complete admin checklist. Cannot approve own patch.

## Gate Enforcement

Gates are checkpoints that must be satisfied before proceeding. See [gate_view_mapping.md](gate_view_mapping.md) for gate-to-view ownership.

| Gate | Owning View | Required Evidence |
|------|-------------|-------------------|
| gate_parse | data_source_panel | row_count, column_headers, parse_timestamp |
| gate_preflight | patch_authoring_view | preflight_report, badge_summary (no fail) |
| gate_evidence | patch_authoring_view | Evidence Pack complete per patch type rules |
| gate_replay | patch_authoring_view | Replay contract satisfied per patch type |
| gate_verifier | verifier_review_view | review_notes, decision_status, checklist confirmed |
| gate_admin | admin_approval_view | admin_action_log, smoke_strict pass |

## Active Data Source Bar (V1.4.9)
- **Location**: Top of sidebar, above Progress block
- **Layout**: Two-line info (label + dataset name) with action pill on right
- **Behavior**: 
  - Shows "No dataset loaded" when empty -> action label: "Connect"
  - Shows dataset filename after load (e.g., "sample_v1.json") -> action label: "Change"
  - Action opens Data Source side panel (not modal)
- **Terminology**: "Active Data Source" (label), "Connect" / "Change" (action)

## Data Source Panel (V1.5)
- **Entry**: "Change" action in Active Data Source bar.
- **Type**: Right-side drawer panel (never modal).
- **Layout order** (active state): Active Dataset card -> Upload|Connect row (two columns) -> Search stub (V2) -> Saved Datasets -> Close.
- **Terminology**: "Data Source" (not "Load Data"), "Disconnect" (not "Remove").

## Terminology

### Roles
- **Analyst**: Default operator role (Stages 1-8)
- **Verifier**: Primary term for the review role (Stage 9)
- **Admin**: Final approval authority (Stage 10-12)

### Patch Lifecycle
- **Patch Draft**: Initial authored patch before submission
- **Patch Request**: Submitted patch awaiting review
- **Approved Patch**: Patch approved by Admin
- **Baseline Patch**: Patch promoted to semantic baseline
- **Promote Patch to Baseline**: The baseline mutation moment (Stage 11)

### Evidence Pack (canonical blocks)
- **Observation** (alias: WHEN) - What situation was observed
- **Expected** (alias: THEN) - What behavior is expected
- **Justification** (alias: BECAUSE) - Why this change is correct
- **Repro** (no alias) - Steps to reproduce

### Replay Contract (v1.6.57)
- **replay_type** - MANUAL, STUBBED, or NA
- **replay_steps** - Steps to replay the change
- **replay_expected_result** - Expected outcome of the replay

### Agent Language
- **Agent suggestion**: For optional AI assistance (never "system" when referring to agents)
- **System-derived**: For deterministic computed values only

## Global Search (V2 Stub)

A search input is present in the top toolbar as a UX placeholder for future functionality.

### Current Behavior (V1)
- Input visible with placeholder: "Search agreements, accounts, record IDs..."
- Keyboard shortcut hint: Cmd+K / Ctrl+K
- On Enter: Shows toast "Search coming soon (V2)"
- No backend indexing, no network calls

### Future Scope (V2)
- Full-text search across loaded records
- Filter by field (agreement, account, contract_key, file_url)
- Results navigate to All Data Grid with filter applied

## Related Documents

- [Flow-Doctrine.md](../V1/Flow-Doctrine.md) - Workflow stages and authority model
- [gate_view_mapping.md](gate_view_mapping.md) - Gate-to-view ownership
- [REVIEW_CHECKLIST.md](../REVIEW_CHECKLIST.md) - Approval checklist items
