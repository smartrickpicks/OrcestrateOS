# Single Row Review View — Authoritative, Per-Record Inspection

Contract: This document defines the record-level inspection surface. It supports Evidence Pack authoring and Patch Draft creation by Analysts while remaining read-only for Verifier/Admin with respect to gates and Review State transitions.

> **UI Label vs Canonical Name**
> - **UI Label (user-facing):** Record Inspection
> - **Canonical Name (specs/audit/routes):** Single Row Review
>
> The user-facing label "Record Inspection" appears in the UI header and navigation. All internal tokens, routes, specs, and audit logs retain the canonical name `single_row_review`.

## Purpose
- Provide authoritative, per-record context: baseline values, deltas, flags, evidence, and audit trail.
- Enable Analysts to author Evidence Packs and create Patch Drafts with explicit rationale and evidence anchoring.
- Maintain strict separation of duties: no direct Review State transitions from this view.

## Roles & Permissions
- Analyst:
  - May edit the Evidence Pack panel to create or update Patch Drafts.
  - May save a Patch Draft and submit as Patch Request for verification; this emits PATCH_DRAFTED and/or PATCH_SUBMITTED and REVIEW_REQUESTED audit events.
  - May add or clear flags with rationale (FLAG_ADDED / FLAG_CLEARED).
- Verifier/Admin:
  - Read-only in this view (inspect baseline, deltas, evidence, and audit log).
  - Gate decisions (STATE_MARKED) occur only in their dedicated governed views (verifier_review_view, admin_approval_view).

## Layout (Three-Panel)

### Top Bar
- Back to Grid button
- Record identity (contract_key or record_id)
- Review State badge (read-only display)
- Open Audit Log button (read-only link)

### Left Panel: Field Inspector (v1.4.1 — Field Cards + Groups/Filters)

**Layout:**
- Group selector dropdown (stub with 3 groups: Identity, Metadata, Status)
- Filter chips: All, Edited, Needs Patch, RFI
- Field Cards (not simple list items)

**Field Card Structure:**
- Header: Label (human-friendly) + API name (monospace), status chips
- Body: Editable value display (click to edit)
- Mini Patch Prompt: Appears after edit with Justification, Comment, Patch Type, Undo

**Status Chips:**
- Edited (orange): Field value has been modified
- Needs Patch (pink): Edited but missing justification
- Required (purple): Schema-defined required field (stub)
- RFI (violet): Marked for RFI category

**Field Ordering Rule (canonical):**
- Primary: Schema order (deterministic, from `SRR_SCHEMA_ORDER`)
- Fallback: Alphabetical for unknown fields not in schema
- V2: Schema order will load from `config/schema.json`

**Inline Editing Behavior:**
- Click value display to enter edit mode
- On blur/Enter: Commit edit, auto-create Proposed Change
- Proposed Change includes: field, label, from, to, category (default: Correction)
- Mini Patch Prompt appears for justification and comment input
- Undo Change button reverts to original value and removes Proposed Change

**Filters:**
- All: Show all fields
- Edited: Show only fields with edits
- Needs Patch: Show edited fields missing justification
- RFI: Show fields marked with RFI category

### Center Panel: Document Viewer (v1.4.10)
- **PDF Rendering**: Displays attached PDFs via browser's native PDF viewer (iframe-based, offline-only)
- **Empty State**: When no PDF is attached, shows placeholder with guidance to attach via Data Source panel
- **Page Navigation**: ← Prev / Next → buttons with page indicator (Page X / Y)
- **Zoom Controls**: + / − buttons with zoom indicator (50% to 300% range, 25% increments)
- **State Persistence**: Per-record page and zoom state persisted to localStorage (keyed by record identity triplet)
- **Evidence Anchors**: Anchor list with click-to-scroll behavior (V2: bbox overlay on PDF)

### Right Panel: Evidence Pack + Patch Request
- Evidence Pack with 4 canonical blocks:
  - **Observation** (helper alias: WHEN) — What situation was observed
  - **Expected** (helper alias: THEN) — What behavior is expected
  - **Justification** (helper alias: BECAUSE) — Why this change is correct
  - **Repro** (no alias) — Steps to reproduce
- Patch Request section:
  - Title: **Patches** with status badge (Draft or Submitted)
  - Proposed changes list (path/before/after)
  - **Save Patch Draft**: Saves Evidence Pack locally, status remains Draft
  - **Submit Patch Request**: Sets patch status to Submitted (local UI state only)
  - Note: Submit updates patch status, **not** Review State. Review State transitions occur only in governed gate views.

## Field-Level Indicators (Deterministic)
For each field:
- state: system_derived | user_modified | flagged
- delta_count: integer (0 for system_derived)
- evidence_count: integer for anchors referencing this field
- last_event_at: timestamp from audit

## Evidence Pack Authoring Contract

The Evidence Pack uses 4 canonical blocks with optional authoring aliases (helper text only):

| Block | Alias | Purpose |
|-------|-------|---------|
| **Observation** | WHEN | Preconditions or context that define applicability |
| **Expected** | THEN | One or more changes (deltas) with path, before, after |
| **Justification** | BECAUSE | Evidence references and plain-language rationale |
| **Repro** | (none) | Steps to reproduce the issue |

Patch Draft authoring emits deterministic events:
- Save Patch Draft → PATCH_DRAFTED with payload { patch_id, changes[], rationale }.
- Submit Patch Request → PATCH_SUBMITTED with payload { patch_id, submission_notes } and REVIEW_REQUESTED { target: "patch", patch_id, reason }.

## Embedded PDF Viewer & Highlights (v1.4.11)

### PDF Source Resolution
PDF source is resolved in priority order:
1. **Network URL**: If record has `file_url` that looks like a PDF URL (ends with `.pdf`, contains `.pdf?`, or `/pdf`), render directly from that URL
2. **Local Attachment (by file_name)**: If a locally attached PDF matches the record's `file_name`, render that
3. **Local Attachment (fallback)**: If any local PDF attachment exists, render the first one
4. **Empty State**: Show "No document attached" with guidance

### Source Indicator
- Shows below controls bar when PDF is loaded
- Format: `[Source Type]: [filename]`
- Source types: "URL" (network) or "Local Attachment"

### Controls (Read-Only via PDF Fragment Params)
Page and zoom are applied using PDF fragment parameters (`#page=N&zoom=percent`):

| Control | Action | Limits |
|---------|--------|--------|
| ← Prev | Go to previous page | Disabled at page 1 |
| Next → | Go to next page | Always enabled (total pages unknown with iframe) |
| − (Zoom Out) | Decrease zoom by 25% | Min: 50% |
| + (Zoom In) | Increase zoom by 25% | Max: 300% |

Page indicator shows "Page X" (without total, as total pages unknown with iframe rendering).

### State Persistence
- Only `{page, zoom}` values are persisted (not objectURL strings)
- Key: `orchestrate.srr_pdf_state.v1` with record identity triplet (contract_key|file_url|file_name)
- State is restored when returning to the same record
- Object URLs are kept in-memory for session only; no stale URL behavior after refresh

### Empty State
When no PDF source is available for the record:
- Shows placeholder icon and message: "No document attached"
- Guidance: "Attach PDFs via Data Source panel to view here"

### Evidence Anchors (V2)
- Evidence anchors will define the page and bbox to highlight
- Click-through mapping:
  - Clicking a field with an associated evidence anchor scrolls the viewer to the anchor's page and highlights the bbox
  - Selecting a highlight focuses the corresponding field in the inspector pane

## Audit Integration
- Opening this view emits a VIEWED event (context: "record").
- All Evidence Pack authoring emits the appropriate PATCH_* events and EVIDENCE_ATTACHED when anchors are added.
- No STATE_MARKED events originate from this view.

## Flags & Warnings
- Analysts can add or clear flags (FLAG_ADDED / FLAG_CLEARED) with category, severity (info | warning | error | critical), and rationale.
- Block conditions are displayed but cannot be resolved here.

## Unsaved Changes Guard

If the user attempts to navigate away (Back to Grid) with edited fields that have incomplete patch data (missing justification), a modal appears:

| Button | Action |
|--------|--------|
| Cancel | Close modal, stay on Single Row Review |
| Discard Changes | Clear all edits and Proposed Changes, navigate to Grid |
| Save Patch Draft | Save current patch draft, then navigate to Grid |

## Navigation
- From All Data Grid → Single Row Review (this view).
- From this view:
  - Open Audit Log detail (read-only overlay or linked panel).
  - Navigate to governed gating views (verifier_review_view, admin_approval_view) via explicit links that do not perform transitions themselves.
  - Back to Grid (guarded if unsaved changes exist).

## Read-Only & Gate Separation
- No approve, promote, or finalize actions are available in this view.
- Review State transitions are owned exclusively by governed gate views.

## Accessibility & Ergonomics
- Keyboard shortcuts:
  - Up/Down: move between fields
  - Enter: expand/collapse field details
  - Ctrl/Cmd+S: Save Patch Draft
  - Ctrl/Cmd+Enter: Submit Patch Request
- Clear legends for indicators and evidence.
- Deterministic ordering and stable scroll positions to aid verification.
