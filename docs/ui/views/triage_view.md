# View: Triage

> Alert summary view showing Review State counts and status cards for quick navigation.

## Recent Changes (v2.3 P0.2)

- **Header IA reorder**: Sections now follow canonical hierarchy: Batch Summary → Contract Summary → Lane Cards → Lifecycle → Schema Snapshot.
- **Batch Summary strip**: New compact row at top showing contracts_total, records_total, completed, needs_review, pending, updated_at. Shows "Unassigned rows" count with tooltip when orphan rows exist.
- **Contract count reconciliation**: Lane + lifecycle totals cross-checked against contract summary. Warning badge shown on mismatch, diagnostic log emitted.
- **Route hardening**: Warning toast shown on final grid fallback. All route decisions logged with `route_decision_record` / `route_decision_contract` / `route_decision_fallback`.
- **Metadata leak guard**: Per-refresh exclusion counters emitted: meta_sheets, ref_sheets, sys_fields.
- **Schema empty-state helper**: Empty-state message shown when schema click-through yields zero results.
- **Layout safezone**: Toast position, FAB, audit dropdown, search bar z-index verified and logged.
- **Logging**: 12 distinct `[TRIAGE-ANALYTICS][P0.2]` events.

## Recent Changes (v2.3 P0.1)

- **Lifecycle count fix**: Removed false "Unassigned (Batch Level)" pseudo-contract from lifecycle denominator. Orphan rows are tracked internally but excluded from contract-level progression counts.
- **Pre-Flight View routing**: Deterministic 3-tier fallback: row-level → Record Inspection, contract-level → filtered grid, final → all-data grid. Logged via `openPreflightItem()`.
- **Patch queue sanitization**: Meta sheets, reference/glossary sheets, and system columns (`__meta*`, `_glossary*`, `_system`, `_internal`) filtered from actionable patch items.
- **System Pass Engine**: Standalone block removed; folded into compact inline control above the System Pass queue.
- **Contract Summary chips**: Collapsed state now shows done/review/pending counts alongside total contracts.
- **Schema snapshot click-through**: Unknown Columns → preflight filter, Missing Required → blocked filter, Schema Drift → needs-review filter.
- **Toast repositioning**: Toasts moved from bottom-right to top-center to avoid Feedback FAB overlap.
- **Search bar vs audit**: Search bar given opaque background; audit dropdown z-index layered below search bar.
- **Logging**: All operations prefixed `[TRIAGE-ANALYTICS][P0.1]`.

## Recent Changes (v2.3 P0)

- **Triage Analytics Header**: Analytics block above existing triage grid with three lane cards (Pre-Flight, Semantic, Patch Review), lifecycle progression tracker, contract summary table, and schema snapshot.
- **Lifecycle Tracker**: 9-stage horizontal strip (Loaded → Applied) with contract-level counts and percentages.
- **Contract Summary Table**: Collapsible table with per-contract stage, alert counts, and "View in Grid" action.
- **Schema Snapshot**: Field match %, unknown columns, missing required, schema drift.

## Recent Changes (v1.5.0)

- **Verifier Triage Mode**: In Reviewer mode, Triage page shows Verifier Triage instead of Analyst Triage
- **Payload Queue System**: RFI, Correction, and Blacklist submissions appear in Verifier queue
- **Queue Tabs**: Pending, Clarification, To Admin, Resolved with live counts
- **Row Click Navigation**: Clicking a triage row opens Verifier Review detail view

## Navigation Entry Points

Triage is accessible via:
- **Progress Block** in sidebar (click routes to #/triage)
- Direct URL navigation (#/triage)

## Entry Conditions

| Condition | Required |
|-----------|----------|
| Dataset loaded | Yes (otherwise redirects to loader) |
| User authenticated | Yes (any role) |
| Minimum role | Analyst |

## Visible Artifacts

| Artifact | Description | Required |
|----------|-------------|----------|
| Review State counts | To Do, Needs Review, Flagged, Blocked, Finalized | Yes |
| Summary cards | Contracts, Ready, Needs Review, Blocked | Yes |
| Data source label | Source name and load timestamp | Yes |
| Filter controls | Search, severity, status, subtype | Yes |
| Triage Analytics Header | Lane cards, lifecycle tracker, contract table, schema snapshot (V2.3) | Yes (after data load) |

## Triage Analytics Header (V2.3 P0 + P0.1 + P0.2)

The analytics header renders above the existing triage grid after data load. It aggregates metrics from existing stores with no data duplication.

### Header Section Order (P0.2)

| # | Section | Description |
|---|---------|-------------|
| 1 | Batch Summary | Compact row with totals, unassigned rows indicator, reconciliation badge |
| 2 | Contract Summary | Collapsible table (collapsed by default) with per-contract detail |
| 3 | Lane Cards | Pre-Flight, Semantic, Patch Review health cards |
| 4 | Lifecycle Progression | 9-stage horizontal tracker |
| 5 | Schema Snapshot | Field matching, unknown columns, drift |

### Batch Summary (P0.2)

Compact horizontal strip showing batch-level totals:

| Metric | ID | Description |
|--------|-----|-------------|
| Contracts | ta-bs-contracts | Total indexed contracts |
| Records | ta-bs-records | Total data rows (excluding meta sheets) |
| Completed | ta-bs-completed | Contracts at "applied" stage |
| Needs Review | ta-bs-review | Contracts with active alerts |
| Pending | ta-bs-pending | Contracts without alerts or completion |
| Updated | ta-bs-updated | Last refresh timestamp |
| Unassigned rows | ta-bs-unassigned | Rows without contract assignment (tooltip explains exclusion policy) |
| Count mismatch | ta-reconcile-warn | Warning badge if lifecycle/contract totals don't reconcile |

### Contract Count Reconciliation (P0.2)

On each refresh, lifecycle stage totals are summed and compared against the contract summary count. If they don't match:
- Warning badge displayed in Batch Summary strip
- Diagnostic log emitted: `lifecycle_reconcile_mismatch` with delta

If they match: `lifecycle_reconcile_ok` logged.

### Data Sources (read-only)

| Source | Data Provided |
|--------|---------------|
| analystTriageState | Pre-flight blocker counts by type |
| SystemPass._proposals | Semantic proposal counts by status |
| PATCH_REQUEST_STORE | Patch lifecycle status counts |
| ContractIndex | Contract-level stage, row counts, sheets |
| rulesBundleCache | Schema field matching, unknown columns |

### Lane A: Pre-Flight

| Counter | Description |
|---------|-------------|
| Unknown Cols | Columns not in canonical schema |
| OCR Unreadable | Document text extraction failures |
| Low Confidence | Extraction confidence below threshold |
| Mojibake | Character encoding corruption |
| Total | Sum of all blocker types |

### Lane B: Semantic

| Counter | Description |
|---------|-------------|
| Proposals | Total System Pass proposals created |
| Accepted | Proposals accepted (non-hinge directly applied) |
| Rejected | Proposals rejected |
| Pending | Proposals awaiting review |
| Hinge | Proposals impacting hinge fields |

### Lane C: Patch Review

| Counter | Description |
|---------|-------------|
| Draft | Patches in draft state |
| Submitted | Patches submitted for review |
| At Verifier | Patches currently with verifier |
| Admin | Patches promoted to admin review |
| RFIs | Request for Information items |
| Promoted | Admin-approved patches |

### Lifecycle Progression Tracker

9-stage horizontal strip showing contract progression. Denominator is real contracts only (orphan/batch-level rows excluded from P0.1).

| Stage | Key | Description |
|-------|-----|-------------|
| Loaded | loaded | Contract indexed from workbook |
| Pre-Flight | preflight_complete | No blockers detected |
| System Pass | system_pass_complete | System Pass has run |
| Reviewed | system_changes_reviewed | All proposals reviewed |
| Patch Sub. | patch_submitted | At least one patch submitted |
| RFI | rfi_submitted | RFI submitted for contract |
| Verifier | verifier_complete | All patches verifier-approved |
| Promoted | admin_promoted | All patches admin-approved |
| Applied | applied | All patches applied |

Click any stage to filter the contract summary table to that stage.

### Contract Summary Table

Collapsible table with columns:

| Column | Description |
|--------|-------------|
| Contract | Display name (file_name or contract_id) |
| Role | Document role from first row |
| Stage | Current lifecycle stage (color-coded badge) |
| Pre-Flight | Alert count for pre-flight blockers |
| Semantic | Alert count for system change proposals |
| Patches | Count of patch requests |
| Rows | Row count in contract |

Collapsed state shows summary chips: total contracts, completed, review, pending.

Actions:
- Click row → navigates to All Data Grid filtered to that contract
- "View in Grid" button → navigates to grid filtered by selected stage

### Schema Snapshot

Clickable mini-panel (P0.1 + P0.2):

| Metric | Click Action | Description |
|--------|--------------|-------------|
| Field Match % | (none) | Percentage of canonical fields found in workbook |
| Unknown Columns | → preflight filter | Columns in workbook but not in field_meta.json |
| Missing Required | → blocked filter | Required canonical fields not found in workbook |
| Schema Drift | → needs-review filter | Sum of unknown + missing required |

If a click-through yields zero results, an empty-state helper message is shown inline (P0.2).

### Pre-Flight View Routing (P0.1 + P0.2)

Deterministic fallback order when clicking a pre-flight item:

1. If row-level record_id exists and found in workbook → open Record Inspection (`route_decision_record`)
2. If contract-level pointer exists → open All Data Grid filtered by contract (`route_decision_contract`)
3. Final fallback → open All Data Grid (unfiltered) with warning toast (`route_decision_fallback`)

No dead ends: the final fallback always navigates to a visible result set with a toast explaining the fallback.

Each decision logged with `[TRIAGE-ANALYTICS][P0.2] route_decision_*`.

### Patch Queue Sanitization (P0.1 + P0.2)

Items filtered from actionable patch queue:
- Rows from meta sheets (change_log, RFIs, etc.)
- Rows from reference/glossary sheets
- Fields starting with `__meta`, `_glossary`, `_system`, `_internal`

P0.2 adds per-type exclusion counters: `meta_sheets`, `ref_sheets`, `sys_fields` emitted in `queue_exclusions_applied` log.

### Console Logging

P0.1 operations log with `[TRIAGE-ANALYTICS][P0.1]` prefix:
- `lifecycle_recompute`: Contract count and orphan exclusion
- `refresh`: Lane totals, contract count, schema match
- `renderHeader`: Display state and contract count

P0.2 operations log with `[TRIAGE-ANALYTICS][P0.2]` prefix (12 events):
- `header_reorder_applied`: Confirms section order applied
- `batch_summary_recomputed`: Batch-level totals with unassigned count
- `contract_summary_recomputed`: Completed/review/pending breakdown
- `lifecycle_reconcile_ok`: Lifecycle and contract totals match
- `lifecycle_reconcile_mismatch`: Lifecycle and contract totals differ (includes delta)
- `route_decision_start`: Route evaluation initiated
- `route_decision_record`: Navigating to Record Inspection
- `route_decision_contract`: Navigating to filtered grid by contract
- `route_decision_fallback`: Final fallback to unfiltered grid with warning toast
- `queue_exclusions_applied`: Per-type exclusion counts (meta_sheets, ref_sheets, sys_fields)
- `snapshot_filter_applied`: Schema card click-through type
- `layout_safezone_applied`: Layout z-index and position verification

### Refresh Triggers

The analytics header refreshes on:
- Dataset load (via `renderAnalystTriage()`)
- System Pass rerun
- Proposal accept/reject
- Patch submit/promote
- Rollback apply

## Allowed Actions by Role

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| View Review State counts | Yes | Yes | Yes |
| View Analytics Header | Yes | Yes | Yes |
| Click lane card (navigate to filtered grid) | Yes | Yes | Yes |
| Click lifecycle stage (filter contract table) | Yes | Yes | Yes |
| Click contract row (navigate to filtered grid) | Yes | Yes | Yes |
| Click schema card (navigate to filtered view) | Yes | Yes | Yes |
| Click status card (navigate to filtered grid) | Yes | Yes | Yes |
| Apply filters | Yes | Yes | Yes |
| Click record row (open inspection) | Yes | Yes | Yes |
| Open Data Source | Yes | Yes | Yes |
| Reset Session | Yes | Yes | Yes |

## Disallowed Actions

| Action | Reason |
|--------|--------|
| Edit record data | Read-only view |
| Submit patches | Navigate to Patch Studio first |
| Approve/reject | Navigate to review views first |
| Access Admin Console | Use sidebar navigation |

## Audit/Evidence Requirements

| Event | Logged |
|-------|--------|
| Page view | No (read-only navigation) |
| Filter change | No (ephemeral UI state) |
| Navigate to record | No (navigation only) |
| Analytics refresh | Console only (`[TRIAGE-ANALYTICS][P0.1]`) |

## State Transitions

This view does not initiate state transitions. It is a navigation hub.

## Verifier Triage (v1.5.0)

When in **Reviewer mode**, the Triage page displays Verifier Triage instead of the Analyst Triage view.

### Mode Switching
- **Analyst mode**: Shows Analyst Triage (status cards, filters, record list)
- **Reviewer mode**: Shows Verifier Triage (payload queue with action buttons)

### Verifier Triage Layout

**Queue Tabs:**

| Tab | Status | Description |
|-----|--------|-------------|
| Pending | `pending` | New submissions awaiting review |
| Clarification | `needs_clarification` | Items requiring analyst response |
| To Admin | `sent_to_admin` | Verifier-approved, awaiting admin |
| Resolved | `resolved` | Completed items |

**Queue Table Columns:**
- Type (RFI / Correction / Blacklist) with color-coded chip
- Record ID / Contract Key
- Field name
- Value (old or new)
- Comment / justification
- Submitted timestamp
- Action buttons

**Verifier Actions:**

| Status | Available Actions |
|--------|-------------------|
| pending | Approve (→ sent_to_admin), RFI (→ needs_clarification) |
| needs_clarification | Re-check (→ pending) |
| sent_to_admin | Finalize (→ resolved) |
| resolved | (no actions) |

### Payload Schema

```javascript
{
  id: string,            // Unique payload ID
  type: 'rfi' | 'correction' | 'blacklist',
  record_id: string,     // Contract key
  field: string,         // Field name
  old_value: string,     // Original value
  new_value: string,     // Proposed value (if applicable)
  comment: string,       // Justification / question
  analyst_id: string,    // Submitting analyst
  timestamp: string,     // ISO timestamp
  status: 'pending' | 'needs_clarification' | 'sent_to_admin' | 'resolved'
}
```

### Persistence

Payloads persist in localStorage (`srr_verifier_queue_v1`) and survive page refresh.

### Row Click Behavior

Clicking any row in the Verifier Triage table:
1. Navigates to Verifier Review page (#/verifier-review)
2. Populates review fields from the selected payload
3. Back button returns to Verifier Triage

## Related Documents

- [data_source_view.md](data_source_view.md) — Data Source panel
- [single_row_review_view.md](single_row_review_view.md) — Single Row Review view
- [verifier_review_view.md](verifier_review_view.md) — Verifier Review view
- [ui_principles.md](../ui_principles.md) — UI principles
- [analyst.md](../roles/analyst.md) — Analyst role permissions
- [verifier.md](../roles/verifier.md) — Verifier role permissions
