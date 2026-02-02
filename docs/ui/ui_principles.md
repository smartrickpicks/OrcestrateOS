# UI Principles (V1)

> Human authority governs all semantic decisions. The UI exists to surface evidence, enable decisions, and record audit trails.

## Product Identity

- **Product name**: Orchestrate OS
- **Primary surface**: Semantic Control Board
- **Logo usage**:
  - Logo is informational, not navigational
  - No homepage metaphor
  - Clicking logo does not trigger state changes
- **Asset location**: `assets/brand/orchestrate-os-logo.png`

## Core Principles

### 1. Evidence-First Display
- Every view must show the artifacts required to make a decision
- No action button appears without visible supporting evidence
- Missing evidence forces a hold or flag state

### 2. Role-Gated Actions
- Actions are hidden (not just disabled) when the user lacks permission
- Role escalation is explicit and logged
- Degraded views show read-only content with clear "no permission" messaging

### 3. State-Driven Navigation
- Navigation reflects data state (empty → load, loaded → triage/grid)
- Gates block forward progression until conditions are met
- Backward navigation preserves context (no data loss)

### 4. Audit by Design
- Every decision-bearing action writes to the audit log
- Timestamps use ISO 8601 format
- Actor identity is captured with role at time of action

### 5. Offline-First Rendering
- All views render from local state (no network fetch for display)
- Evidence artifacts are snapshots, not live queries
- Determinism: same state produces identical UI

## Review State Transition Matrix

This matrix defines the allowed state transitions for patch requests. Only the specified roles may initiate each transition.

| From State | To State | Initiating Role | Trigger Action |
|------------|----------|-----------------|----------------|
| Draft | Submitted | Analyst, Verifier, Admin | Submit Patch Request |
| Submitted | Under_Review | Verifier, Admin | Begin Review |
| Under_Review | Needs_Clarification | Verifier, Admin | Request Clarification |
| Needs_Clarification | Submitted | Analyst, Verifier, Admin | Respond to Clarification |
| Under_Review | Verifier_Approved | Verifier, Admin | Approve (Verifier) |
| Under_Review | Rejected | Verifier, Admin | Reject |
| Verifier_Approved | Admin_Approved | Admin | Approve (Admin) |
| Verifier_Approved | Admin_Hold | Admin | Hold |
| Admin_Hold | Under_Review | Admin | Release Hold |
| Admin_Approved | Applied | Admin | Promote Patch to Baseline |
| Applied | Promoted | Admin | Export to PR |

## Gate Enforcement

Gates are checkpoints that must be satisfied before proceeding. See [gate_view_mapping.md](gate_view_mapping.md) for gate-to-view ownership.

| Gate | Owning View | Required Evidence |
|------|-------------|-------------------|
| gate_parse | data_source_panel | row_count, column_headers, parse_timestamp |
| gate_preflight | patch_authoring_view | preflight_report, badge_summary (no fail) |
| gate_evidence | patch_authoring_view | 4-block Evidence Pack complete (Observation, Expected, Justification, Repro) |
| gate_verifier | verifier_review_view | review_notes, decision_status |
| gate_admin | admin_approval_view | admin_action_log |

## Data Source Panel (V1.5)
- **Entry**: Top quick-action "Data Source" button only (not in sidebar).
- **Type**: Right-side drawer panel (never modal).
- **Layout order** (active state): Active Dataset card → Upload|Connect row (two columns) → Search stub (V2) → Saved Datasets → Close.
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
- **Observation** (alias: WHEN) — What situation was observed
- **Expected** (alias: THEN) — What behavior is expected
- **Justification** (alias: BECAUSE) — Why this change is correct
- **Repro** (no alias) — Steps to reproduce

### Agent Language
- **Agent suggestion**: For optional AI assistance (never "system" when referring to agents)
- **System-derived**: For deterministic computed values only

## Global Search (V2 Stub)

A search input is present in the top toolbar as a UX placeholder for future functionality.

### Current Behavior (V1)
- Input visible with placeholder: "Search agreements, accounts, record IDs…"
- Keyboard shortcut hint: ⌘K / Ctrl+K
- On Enter: Shows toast "Search coming soon (V2)"
- No backend indexing, no network calls

### Future Scope (V2)
- Full-text search across loaded records
- Filter by field (agreement, account, contract_key, file_url)
- Results navigate to All Data Grid with filter applied

## Related Documents

- [Flow-Doctrine.md](../V1/Flow-Doctrine.md) — Workflow stages and authority model
- [gate_view_mapping.md](gate_view_mapping.md) — Gate-to-view ownership
- [REVIEW_CHECKLIST.md](../REVIEW_CHECKLIST.md) — Approval checklist items
