# All Data Grid View — Bulk Inspection (Read-Only)

Contract: This document defines the bulk inspection grid. It is read-only and provides navigation to record-level inspection without permitting edits, gates, or transitions.

## Purpose
- Provide a scalable, filterable, and sortable overview of all records.
- Surface critical indicators (system-derived vs user-modified, flags, warnings, blocked status) at a glance.
- Route operators into the Single Row Review view for detailed work.

## Read-Only Guarantees
- No cell editing, no inline patching, no state transitions.
- No gates are present in this view; navigation surfaces never perform state transitions.

## Visual Indicators
Per row, the grid must display:
- Review State badge: one of [To Do, Needs Review, Flagged, Blocked, Finalized].
- Modification marker:
  - System-derived: fields with values populated by baseline ingestion (no user deltas) are shown with a neutral indicator.
  - User-modified: fields with pending or applied patches show a distinct indicator (e.g., blue dot or pencil icon) and a count of deltas.
- Flags & warnings:
  - Flag icon with severity (info, warning, error, critical) and count.
  - Blocked indicator if any active block condition is present.
- Evidence presence: small paperclip icon with count of evidence anchors.

## Columns (Minimum Set)
- record_id (string)
- dataset_id (string)
- review_state (badge)
- flags (count + highest severity)
- warnings (count)
- modified_fields (count)
- last_event_at (timestamp from audit log)

Additional columns may be added if purely informational and read-only.

## Sorting & Filtering
- Sortable by any visible column; default sort by last_event_at desc.
- Filters: review_state, flags.severity, dataset_id, modified_fields > 0, text search across record_id and key fields.

## Navigation
- Row click opens Single Row Review for that record in a new governed route.
- Deep links: the grid may display links to evidence counts that route to Single Row Review with the evidence panel pre-opened.
- No other destinations (e.g., no direct links to approval or promotion views).

## Empty & Error States
- Empty results: display guidance to load data (link opens Load Data modal) or adjust filters.
- Error fetching display data: show read-only error banner; do not offer retry that would imply runtime execution.

## Performance & Offline Behavior
- Pagination is deterministic; page size is fixed or user-selectable from a small set of options.
- All rows are derived from repository-bound data; no network lookups.

## Accessibility & Ergonomics
- Keyboard accessible row focus and navigation.
- Clear legend for indicators (system-derived, user-modified, flags, blocked).
- Tooltips reveal counts and short explanations; never perform actions.
