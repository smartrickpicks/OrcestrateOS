# View: Triage

> Alert summary view showing Review State counts and status cards for quick navigation.

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

## Allowed Actions by Role

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| View Review State counts | Yes | Yes | Yes |
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
