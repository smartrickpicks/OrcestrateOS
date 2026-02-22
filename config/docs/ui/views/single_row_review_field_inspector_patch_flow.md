# Record Inspection: Field Inspector Patch Flow

> v1.4.18 — Field-level editing with patch creation via local queue.

## Overview

The Field Inspector Patch Flow enables analysts to edit field values directly within the Record Inspection view, create structured evidence packs, and submit patch requests to the local Patch Console queue.

## Implementation Status (v1.4.18)

| Feature | Status |
|---------|--------|
| Search input (field name/value filter) | Done |
| Filter chips: All / Changed / Unchanged | Done |
| Inline field editing (click to edit) | Done |
| Field lock on commit with Changed marker | Done |
| Patch Editor block (Old/New values) | Done |
| Patch Editor sync with Field Inspector | Done |
| Evidence Pack dropdowns + notes | Done |
| Repro file attachment | Done |
| Submit validation (Observation + Expected + at least one change) | Done |
| Patch Request creation to Patch Console | Done |

## Acceptance Criteria

| ID | Criteria | Status |
|----|----------|--------|
| AC-01 | Field edit locks and marks Changed | ✓ Pass |
| AC-02 | Patch Editor old/new values stay in sync | ✓ Pass |
| AC-03 | Evidence Pack inputs persist in draft | ✓ Pass |
| AC-04 | Submit creates Patch Request visible in Patch Console | ✓ Pass |
| AC-05 | Search + Changed/Unchanged filters work | ✓ Pass |

## UI Components

### Left Panel: Field Inspector

1. **Search Bar**
   - Input field filters by field name or value
   - Real-time filtering as user types

2. **Filter Chips**
   - All: Show all fields
   - Changed: Show only locked/committed fields
   - Unchanged: Show fields not yet modified

3. **Field Cards**
   - Display field name (human-friendly label)
   - Display current value (click to edit)
   - Chips: Changed (green), Locked (🔒), Required
   - Locked fields cannot be edited inline (use Patch Editor)

### Right Panel: Patch Editor

1. **Changed Fields Section**
   - Shows count of changes
   - Per-field blocks with:
     - Field label + remove button
     - Old value (locked, dimmed, strikethrough style)
     - New value (editable input)
   - Editing new value syncs to Field Inspector display

2. **Evidence Pack**
   - **Observation (WHEN)**: Dropdown + optional notes
     - Options: Incorrect Value, Missing Value, Formatting Issue, Duplicate Entry, Inconsistent Data, Other
   - **Expected (THEN)**: Dropdown + optional notes
     - Options: Use Correct Value, Populate Empty Field, Standardize Format, Remove Duplicate, Align with Source Document, Other
   - **Justification (BECAUSE)**: Textarea
   - **Repro**: Dropdown + optional notes + file input
     - Options: Visual Inspection of Document, Data Comparison, Rule Violation Detected, Verified Against External Source, Other

3. **Actions**
   - Save Draft: Persists evidence pack to local state
   - Submit Patch Request: Validates and creates patch request

## Workflow

1. **Load Record**: Navigate to a row in the grid, opens Record Inspection
2. **Search/Filter**: Use search input or filter chips to find fields
3. **Edit Field**: Click field value to enter edit mode
4. **Commit Edit**: Press Enter or blur to commit; field locks
5. **Review in Patch Editor**: Changed fields appear in right panel
6. **Modify New Value**: Edit in Patch Editor if needed (syncs back)
7. **Fill Evidence Pack**: Select dropdowns, add notes/justification
8. **Submit**: Click Submit Patch Request

## Validation Rules

- **Observation type**: Required (must select from dropdown)
- **Expected type**: Required (must select from dropdown)
- **At least one change**: Required (must have committed field edits)
- **Justification**: Optional but recommended

## State Management

```javascript
srrState = {
  originalValues: {},      // Snapshot of record values on load
  editedValues: {},        // Current edited values
  proposedChanges: {},     // Change objects per field
  lockedFields: {},        // Fields locked after commit
  searchQuery: '',         // Current search filter
  activeFilter: 'all',     // all | changed | unchanged
  patchDraft: {
    observation_type: '',
    observation_notes: '',
    expected_type: '',
    expected_notes: '',
    justification: '',
    repro_type: '',
    repro_notes: '',
    repro_file: null,
    changes: [],
    status: 'Draft'
  }
}
```

## Patch Request Creation

When submitted, creates a `PatchRequest` with:
- `record_identity`: contract_key, file_url, file_name
- `target_scope`: contract section, field (or "multiple" if >1 field changed)
- `intent_structured`: condition_type=FIELD_VALUE, action_type=SET_VALUE
- `evidence`: Observation, Expected, Justification, Repro blocks
- `proposed_change`: Summary of old → new values

The request is added to `patchRequestsStore` and appears in Patch Console.

## Non-Goals

- No PDF parsing or auto-extraction
- No backend sync (demo/offline only)
- No system auto-rules
- No multi-user collaboration

## Files

- `ui/viewer/index.html`: Main implementation
- `docs/ui/views/single_row_review_field_inspector_patch_flow.md`: This document
