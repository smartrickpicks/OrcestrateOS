# View: Triage

> Alert summary view showing Review State counts and status cards for quick navigation.

## Recent Changes (v2.3.5 P1D.1)

- **Contract Health Pre-Flight Table**: Replaced fragmented per-contract card blocks with a single unified nested table. Parent rows represent contracts (accordion expand/collapse), child rows are individual issues.
- **Parent row schema**: Expand icon, contract name, compact ID, source/domain hint, total issue count, severity summary badges (blocker/warning), contract section chips (e.g., Accounts(3), Financials(1)), "View Contract" quick action.
- **Child row schema**: Contract Section (renamed from Sheet), Reference (business identifier lookup), Issue (human-readable reason chip), Severity, Status, View/Patch actions.
- **Counting semantics**: Affected Contracts = unique `contract_id` with ≥1 pre-flight issue (not flat issue count). Records Impacted = unique `record_id` under affected contracts. Distinct from total issue rows.
- **Grouping model**: Grouped map keyed by `contract_id` (fallback: batch-level bucket). Explicit "Batch-level (Unassigned)" group for unresolved scope. Parent rows sorted by blocker count desc → issue count desc → name asc.
- **OCR taxonomy**: OCR is parent bucket. Mojibake remains child reason under OCR. One parent per contract regardless of child issue count.
- **Routing**: Parent "View Contract" routes to contract-filtered all-data-grid. Child "View" uses existing resolver chain. Unresolved items show diagnostic modal (no dead-end toasts).
- **Terminology**: "Sheet" → "Contract Section" in Pre-Flight nested table.
- **Logging**: 5 events with `[TRIAGE-CONTRACT-HEALTH][P1D.1]` prefix: `model_built`, `parent_rows_rendered`, `child_rows_rendered`, `group_toggled`, `metrics_recomputed`.

## Recent Changes (v2.3 P1)

- **Live telemetry cache**: `TriageTelemetry` aggregator keyed by active dataset with `files_total`, `files_processed`, `processing_state` (idle|running|stale|complete), `lane_counts`, `lifecycle_stage_counts`, `last_updated_at`. Recomputed on upload load, demo/sandbox load, restore/session load, pre-flight rerun, system pass rerun, patch status transitions, and audit events.
- **Lifecycle progression enhancements**: Per-stage `count`, `percentage`, and `delta` since prior refresh. Delta badges shown below each stage (green +N / red -N). Throughput metric (`items/min`) computed when `processing_state=running`.
- **Lane drill-down hardening**: Clicking any lane card applies deterministic filter to contract summary table. Toggle behavior (click again to clear). Clear-filter badge shown in contract section header. Active lane filter persisted across renders.
- **Contract state chips**: Derived chips per contract: `preflight_blocked`, `semantic_pending`, `patch_pending`, `ready_for_verifier`, `promoted`. Clickable — each filters contract summary table. Derivation from current status/signals/events only.
- **Processing status banner**: Compact status line above batch summary: shows processing state icon, file counts, dominant lifecycle stage, last update time. Stale indicator when no update for 60s (configurable). "Up to date" when complete/idle. State transitions: idle → running → complete (or stale).
- **Event→stage mapping table**: Explicit mapping in `TriageTelemetry.EVENT_STAGE_MAP` for how events affect lifecycle counters. 16 event types mapped. Dedupe key (`event_id` or stable composite) prevents double counting.
- **Performance guardrails**: 300ms debounce on telemetry UI refresh via `debouncedRefresh()`. Partial rerender for counters (no full contract table rebuild when only counts change). Warm refresh responsive for demo-scale datasets.
- **Logging**: 8 distinct `[TRIAGE-ANALYTICS][P1]` events: `telemetry_recompute`, `event_stage_mapped`, `event_dedupe_hit`, `lifecycle_refresh`, `lane_filter_applied`, `processing_state_changed`, `stale_state_entered`, `stale_state_cleared`.

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
- **Patch queue sanitization**: Meta sections, reference/glossary sections, and system columns (`__meta*`, `_glossary*`, `_system`, `_internal`) filtered from actionable patch items.
- **System Pass Engine**: Standalone block removed; folded into compact inline control above the System Pass queue.
- **Contract Summary chips**: Collapsed state now shows done/review/pending counts alongside total contracts.
- **Schema snapshot click-through**: Unknown Columns → preflight filter, Missing Values → blocked filter, Data Quality → data quality modal.
- **Toast repositioning**: Toasts moved from bottom-right to top-center to avoid Feedback FAB overlap.
- **Search bar vs audit**: Search bar given opaque background; audit dropdown z-index layered below search bar.
- **Logging**: All operations prefixed `[TRIAGE-ANALYTICS][P0.1]`.

## Recent Changes (v2.3 P0)

- **Triage Analytics Header**: Analytics block above existing triage grid with three lane cards (Pre-Flight, Semantic, Patch Review), lifecycle progression tracker, contract summary table, and schema snapshot.
- **Lifecycle Tracker**: 9-stage horizontal strip (Loaded → Applied) with contract-level counts and percentages.
- **Contract Summary Table**: Collapsible table with per-contract stage, alert counts, and "View in Grid" action.
- **Schema Snapshot**: Columns Mapped %, Unknown Columns, Missing Values, Data Quality.

## Recent Changes (v1.5.0)

- **Verifier Triage Mode**: In Verifier mode, Triage page shows Verifier Triage instead of Analyst Triage
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
| Triage Analytics Header | Processing banner, batch summary, contract table, lane cards, lifecycle tracker, schema snapshot (V2.3 P0-P1) | Yes (after data load) |

## Triage Analytics Header (V2.3 P0 + P0.1 + P0.2 + P1)

The analytics header renders above the existing triage grid after data load. It aggregates metrics from existing stores with no data duplication.

### Header Section Order (P0.2 + P1)

| # | Section | Description |
|---|---------|-------------|
| 0 | Processing Banner (P1) | Compact status line: state icon, file counts, dominant stage, stale indicator |
| 1 | Batch Summary | Compact row with totals, unassigned rows indicator, reconciliation badge |
| 2 | Contract Summary | Collapsible table (collapsed by default) with per-contract detail + state chips (P1) |
| 3 | Lane Cards | Pre-Flight, Semantic, Patch Review health cards (with drill-down filter P1) |
| 4 | Lifecycle Progression | 9-stage horizontal tracker with deltas and percentages (P1) |
| 5 | Schema Snapshot | Columns Mapped, Unknown Columns, Missing Values, Data Quality |

### Batch Summary (P0.2)

Compact horizontal strip showing batch-level totals:

| Metric | ID | Description |
|--------|-----|-------------|
| Contracts | ta-bs-contracts | Total indexed contracts |
| Records | ta-bs-records | Total data rows (excluding meta sections) |
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
| ContractIndex | Contract-level stage, row counts, contract sections |
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
| Columns Mapped | (none) | Percentage of uploaded columns recognized against the governed glossary |
| Unknown Columns | → preflight filter | Columns in workbook not recognized in the governed glossary. Supports decision classification: add to glossary (global), mark as source-specific, or ignore. Glossary link opens searchable picker. |
| Missing Values | → blocked filter | Required fields that are missing or empty. Includes blank-like values and invalid picklist entries with per-reason breakdown. |
| Data Quality | → data quality modal | Combined count of duplicate account candidates and incomplete address candidates. Opens the Data Quality Check modal. |

If a click-through yields zero results, an empty-state helper message is shown inline (P0.2).

### Pre-Flight Contract Health Table (P1D.1)

The Pre-Flight queue renders as a single nested table (not individual cards per contract). Rows are split into two types:

**Parent Rows** (contract-level, clickable to expand/collapse):

| Column | Description |
|--------|-------------|
| Expand Icon | ▶ collapsed / ▼ expanded |
| Contract | Display name (from file_name, cleaned) |
| ID | Compact contract_key (truncated to 22 chars) |
| Source | Domain hint extracted from file_url |
| Issues | Total issue count for this contract |
| Severity | Blocker/warning count badges |
| Contract Sections | Chips per section with counts, e.g., Accounts(3) |
| Actions | "View Contract" button → routes to contract-filtered all-data-grid |

**Child Rows** (issue-level, hidden when parent collapsed):

| Column | Description |
|--------|-------------|
| Contract Section | Sheet name (renamed from "Sheet") |
| Reference | Business identifier resolved from workbook row data |
| Issue | Human-readable reason chip with tooltip |
| Severity | Blocker (red) or Warning (orange) |
| Status | Open/Resolved badge |
| Actions | View (opens resolver chain) / Patch (when applicable) |

**Sorting**: Parent rows ordered by blocker count desc → issue count desc → name asc. Batch-level group always last.

**Expand/Collapse**: First 5 groups expanded by default, rest collapsed. State persisted during session.

**Metric Semantics**:
- Affected Contracts = count of unique `contract_id` values with ≥1 pre-flight issue
- Records Impacted = count of unique `record_id` values under affected contracts
- These are distinct from total issue row count (one contract may have many issues)

### Pre-Flight View Routing (P0.1 + P0.2)

Deterministic fallback order when clicking a pre-flight item:

1. If row-level record_id exists and found in workbook → open Record Inspection (`route_decision_record`)
2. If contract-level pointer exists → open All Data Grid filtered by contract (`route_decision_contract`)
3. Final fallback → open All Data Grid (unfiltered) with warning toast (`route_decision_fallback`)

No dead ends: the final fallback always navigates to a visible result set with a toast explaining the fallback.

Each decision logged with `[TRIAGE-ANALYTICS][P0.2] route_decision_*`.

### Patch Queue Sanitization (P0.1 + P0.2)

Items filtered from actionable patch queue:
- Rows from meta sections (change_log, RFIs, etc.)
- Rows from reference/glossary sections
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
- Pre-flight rerun (P1)
- Patch status transitions (P1)
- Relevant audit events (P1 — via `TriageTelemetry.processEvent()`)

## Triage Telemetry (V2.3 P1)

### Processing Status Banner

Compact status bar above the Batch Summary strip. State transitions:

| State | Icon | Background | Description |
|-------|------|-----------|-------------|
| idle | ● | grey | No data loaded |
| running | ⚙ | blue | Processing files (shows X/Y count) |
| stale | ⚠ | orange | No update for 60s (configurable via `_staleTimeoutMs`) |
| complete | ✓ | green | All files processed, "Up to date" |

DOM elements: `ta-processing-banner`, `ta-proc-icon`, `ta-proc-text`, `ta-proc-detail`, `ta-proc-stage`, `ta-proc-time`, `ta-proc-throughput`, `ta-proc-stale`.

### Lifecycle Deltas and Percentages (P1)

Each lifecycle stage element receives two additional sub-elements:
- `.ta-stage-delta`: Shows +N (green) or -N (red) change since prior refresh
- `.ta-stage-pct`: Shows percentage of total contracts at that stage

Throughput (`items/min`) is shown in the processing banner when `processing_state=running`.

### Lane Drill-Down (P1)

Clicking a lane card triggers `TriageTelemetry.applyLaneFilter(lane)`:
1. Filters contract summary table to contracts with alerts in that lane
2. Expands the contract summary table
3. Shows filter badge in contract section header with lane name + ✕
4. Click badge or click same lane again to clear filter

Toggle behavior: clicking the same lane twice clears the filter.

### Contract State Chips (P1)

Derived chips rendered in the contract summary header:

| Chip | Derivation |
|------|-----------|
| PF Blocked | `preflight_alerts > 0` |
| Sem. Pending | `semantic_alerts > 0` |
| Patch Pending | `patch_alerts > 0` |
| Ready for Verifier | `current_stage` is `verifier_complete` or `system_changes_reviewed` |
| Promoted | `current_stage` is `admin_promoted` or `applied` |

Each chip is clickable and filters the contract summary table.

### Event → Stage Mapping (P1)

`TriageTelemetry.EVENT_STAGE_MAP` defines how events map to lifecycle stages:

| Event | Target Stage | Delta |
|-------|-------------|-------|
| dataset_loaded | loaded | +1 |
| file_parsed | loaded | +1 |
| preflight_complete | preflight_complete | +1 |
| preflight_blocker_detected | loaded | 0 |
| system_pass_complete | system_pass_complete | +1 |
| proposal_accepted | system_changes_reviewed | +1 |
| proposal_rejected | system_changes_reviewed | +1 |
| system_change_routed_to_patch | patch_submitted | +1 |
| patch_submitted | patch_submitted | +1 |
| rfi_submitted | rfi_submitted | +1 |
| VERIFIER_APPROVED | verifier_complete | +1 |
| VERIFIER_REJECTED | verifier_complete | +1 |
| ADMIN_APPROVED | admin_promoted | +1 |
| patch_applied | applied | +1 |
| rollback_applied | loaded | 0 |
| schema_change | (none) | 0 |

Deduplication: Events are keyed by `event_id` (if present) or composite `eventType::record_id::contract_id::field_key::artifact_id`. Duplicate events log `event_dedupe_hit`.

### P1 Console Logging

All P1 operations log with `[TRIAGE-ANALYTICS][P1]` prefix:

| Event | Description |
|-------|-------------|
| telemetry_recompute | State, file counts, lane totals |
| event_stage_mapped | Event type → stage mapping applied |
| event_dedupe_hit | Duplicate event key detected |
| lifecycle_refresh | Debounced lifecycle UI refresh |
| lane_filter_applied | Lane drill-down filter activated |
| processing_state_changed | Processing state transition (from → to) |
| stale_state_entered | Stale timeout reached |
| stale_state_cleared | Stale state cleared by new data |

### Performance Guardrails (P1)

- `debouncedRefresh()`: 300ms debounce on telemetry UI refresh
- Partial rerender: `renderLifecycleDeltas()` and `renderContractChips()` update only their DOM targets without full table rebuild
- `renderBanner()` only touches banner DOM elements
- Stale timer managed via `_resetStaleTimer()` — auto-clears on recompute

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
| Analytics refresh | Console only (`[TRIAGE-ANALYTICS][P0.1]`, `[P0.2]`, `[P1]`) |
| Telemetry recompute | Console only (`[TRIAGE-ANALYTICS][P1]`) |
| Lane filter applied | Console only (`[TRIAGE-ANALYTICS][P1]`) |
| Processing state change | Console only (`[TRIAGE-ANALYTICS][P1]`) |

## State Transitions

This view does not initiate state transitions. It is a navigation hub.

## Verifier Triage (v1.5.0)

When in **Verifier mode**, the Triage page displays Verifier Triage instead of the Analyst Triage view.

### Mode Switching
- **Analyst mode**: Shows Analyst Triage (status cards, filters, record list)
- **Verifier mode**: Shows Verifier Triage (payload queue with action buttons)

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
- [single_row_review_view.md](single_row_review_view.md) — Record Inspection view
- [verifier_review_view.md](verifier_review_view.md) — Verifier Review view
- [ui_principles.md](../ui_principles.md) — UI principles
- [analyst.md](../roles/analyst.md) — Analyst role permissions
- [verifier.md](../roles/verifier.md) — Verifier role permissions
