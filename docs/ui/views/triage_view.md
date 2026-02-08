# View: Triage

> Alert summary view showing Review State counts and status cards for quick navigation.

## Recent Changes (v2.3)

- **Triage Analytics Header (P0)**: New analytics block above existing triage grid with three lane cards (Pre-Flight, Semantic, Patch Review), lifecycle progression tracker, contract summary table, and schema snapshot.
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

## Triage Analytics Header (V2.3 P0)

The analytics header renders above the existing triage grid after data load. It aggregates metrics from existing stores with no data duplication.

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

9-stage horizontal strip showing contract progression:

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

Actions:
- Click row → navigates to All Data Grid filtered to that contract
- "View in Grid" button → navigates to grid filtered by selected stage

### Schema Snapshot

Read-only mini-panel showing:

| Metric | Description |
|--------|-------------|
| Field Match % | Percentage of canonical fields found in workbook |
| Matched / Total | Count of matched vs total canonical fields |
| Unknown Columns | Columns in workbook but not in field_meta.json |
| Missing Required | Required canonical fields not found in workbook |
| Schema Drift | Sum of unknown + missing required |

### Console Logging

All analytics operations log with `[TRIAGE-ANALYTICS][P0]` prefix:
- `refresh`: Outputs lane totals, contract count, schema match
- `renderHeader`: Outputs display state and contract count

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
| Analytics refresh | Console only (`[TRIAGE-ANALYTICS][P0]`) |

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
