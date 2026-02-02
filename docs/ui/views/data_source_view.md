# Data Source View — Governed Data Loading UX

Contract: This document defines the governed, offline-first Data Source experience. It specifies UI placement, allowed inputs, deterministic behaviors, switching states, audit requirements, and role semantics. It does not define implementation code or runtime ingestion services.

## Placement & Access
- Entry: **Top quick-action bar only** ("Data Source" button). No sidebar nav item.
- Behavior: Always opens the right-side panel regardless of data state.
- Roles: Analysts and Admins may add or switch data sources. Verifiers may view in read-only preview mode.

## Data Source States (Deterministic)

### State A: No Data (Empty State)
- **Condition**: No active dataset loaded.
- **Display**: Right-side panel with:
  - Empty state card: "No Active Dataset"
  - In-panel upload dropzone (CSV/XLSX)
  - Demo Dataset load button
  - Connect stubs: "Connect Google Drive (V2)" disabled, "Connect MCP Source (V2)" disabled
- **Affordances**: Upload CSV/XLSX, load demo dataset.

### State B: Active Dataset
- **Condition**: Active dataset loaded.
- **Display**: Right-side panel with:
  - Active Dataset card with name, row count, loaded timestamp, "ACTIVE ▾" badge.
  - ACTIVE badge has hover menu with "Disconnect" action.
  - "Upload New Dataset" dropzone (uploading rotates previous active to Saved).
  - Saved Datasets list (if any exist).
  - Connect stubs (disabled, Coming in V2).
- **Affordances**: View metadata, disconnect, upload new, select from Saved.

## Active Dataset Constraints

### Delete Protection
- **Active dataset cannot be deleted.**
- Delete button is disabled with tooltip: "Disconnect first."
- User must Disconnect (via ACTIVE badge click menu) before deleting.

### Disconnect Action
- Location: Click menu on ACTIVE badge in Active Dataset card (click to reveal dropdown).
- Behavior:
  1. Move active dataset into Saved Datasets list.
  2. Clear active dataset pointer (`activeDatasetId = null`).
  3. Keep panel open; switch UI to empty/connect state.

### Upload Rotation Rule
- When uploading a new dataset while an active dataset exists:
  1. Move previous active dataset into Saved Datasets.
  2. Set new dataset as Active.
- This prevents data loss while maintaining single-active invariant.

## Switching Datasets (V1 Contract)
- Switching datasets **does not alter Review States**.
- Review States (To Do, Needs Review, Flagged, Blocked, Finalized) are preserved per-dataset.
- Switching only changes the active dataset context for display.
- Audit event: DATASET_SWITCHED (not STATE_MARKED).

## Connector Language (V1)
- **V1 Default**: Connect stubs are always visible but disabled.
- **Stub buttons**: 
  - "Connect Google Drive" — disabled, badge: "V2"
  - "Connect MCP Source" — disabled, badge: "V2"
- **Label**: "Coming in V2" below the stubs.
- **No feature flag gating**: Stubs are always visible to set expectations.

## Supported Inputs & Parity
- Accepted file types: CSV and Excel (.xlsx).
- Parity statement:
  - CSV and Excel receive identical validation and mapping flows.
  - For Excel, each worksheet is treated as a logical dataset; the user selects one worksheet per load operation.
  - No formula evaluation; values are treated as static cell contents.

## Copy-Only Ingestion
- The loader performs copy-only ingestion: source files are copied into repository-bound storage without mutation.
- No external services, no network calls, no runtime hooks.
- A normalization plan is presented before confirmation (headers, column count, detected types), but the source bytes remain unchanged.

## Deterministic Defaults
- Header detection: user chooses one of [Has header row, No header row]. Default: Has header row.
- Column normalization: spaces trimmed, internal whitespace collapsed, consistent casing (e.g., snake_case) applied to headers if the user opts in.
- Null handling: empty cells normalized to null.
- Date handling: values are ingested as strings; no implicit timezone or format conversion.

## Initial Review State
- All records created via this view are initialized with Review State: "To Do".
- The view must not emit state transitions. No auto-review, no implicit promotion.

## Audit Requirements
Upon successful data load, emit exactly one LOADED event per dataset with payload fields:
- file_path (repository-relative)
- file_format (csv | xlsx)
- sheet_name (xlsx only; otherwise null)
- row_count, column_count
- headers (array of strings)
- source_checksum (hex digest of source file bytes)

Additionally:
- Emit VIEWED event when the modal/drawer is opened (context: "dataset").
- Emit DATASET_SWITCHED event when switching active datasets.

## User Flow

### Adding Data Source (Panel — No Modal)
1) **Click Data Source** button in top quick-action bar.
2) **Panel opens** showing current state (empty or active).
3) **Upload file** via dropzone or **Load Sample** via button.
4) **Preview** first N rows in read-only grid.
5) **Confirm Load** — copy source file, emit LOADED event, set as Active.

### Switching Data Source (Panel)
1) **Open Data Source** from top quick-action bar.
2) **View Active Dataset** card with ACTIVE badge.
3) **Select from Saved Datasets** list to switch.
4) **Dataset Switched** — context updates, Review States preserved.

### Disconnecting Active Dataset
1) **Click ACTIVE badge** to reveal dropdown menu.
2) **Click Disconnect** action.
3) **Active moves to Saved** — UI transitions to empty state.
4) **Panel stays open** for immediate next action.
5) **Dataset Switched** — context updates, Review States preserved.

## Error States (Display Only)
- Non-parsable file: render error banner; no partial commit; audit a VIEWED event only.
- Header mismatch: present a clear message and allow toggling header detection; no auto-fix.

## Read-Only Guarantees
- The loader does not edit the source file content.
- The loader does not create or modify patches.
- No gates are present in this view.

## Accessibility & Ergonomics
- Keyboard navigation for file selection and preview table.
- Clear labeling of CSV/Excel parity and copy-only behavior.
- Visible badge in the summary indicating: "Initial Review State: To Do".
- ESC key closes modal/drawer.
