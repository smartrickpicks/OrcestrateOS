# View: Triage

> Alert summary view showing Review State counts and status cards for quick navigation.

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

## Related Documents

- [data_source_view.md](data_source_view.md) — Data Source panel
- [single_row_review_view.md](single_row_review_view.md) — Single Row Review view
- [ui_principles.md](../ui_principles.md) — UI principles
- [analyst.md](../roles/analyst.md) — Analyst role permissions
