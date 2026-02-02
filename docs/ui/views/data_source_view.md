# Data Source View — Governed Data Loading UX

Contract: This document defines the governed, offline-first Data Source experience. It specifies UI placement, allowed inputs, deterministic behaviors, switching states, audit requirements, and role semantics. It does not define implementation code or runtime ingestion services.

## Placement & Access
- Entry: Sidebar item "Data Source" under the "Data" section.
- Behavior: Opens contextual panel based on current state (see Data Source States below).
- Roles: Analysts and Admins may add or switch data sources. Verifiers may view in read-only preview mode.

## Data Source States (Deterministic)

### State A: No Data
- **Condition**: No data loaded AND no saved datasets in browser storage.
- **Display**: Centered modal with "Add Data Source" CTA.
- **Affordances**: Upload CSV, load demo dataset.

### State B: Active (Single Dataset)
- **Condition**: Data loaded, one dataset in session.
- **Display**: Data Source drawer showing:
  - Active Dataset card with name, row count, loaded timestamp, "ACTIVE" badge.
  - "Add Data Source" button in footer.
- **Affordances**: View active dataset metadata, add new data source.

### State C: Multiple Datasets
- **Condition**: Data loaded, multiple datasets in browser storage.
- **Display**: Data Source drawer showing:
  - Active Dataset card (as in State B).
  - "Switch Data Source" button with note: "Switching datasets does not alter Review States".
  - Saved Datasets list with selection affordance.
- **Affordances**: Switch between datasets, add new data source.

## Switching Datasets (V1 Contract)
- Switching datasets **does not alter Review States**.
- Review States (To Do, Needs Review, Flagged, Blocked, Finalized) are preserved per-dataset.
- Switching only changes the active dataset context for display.
- Audit event: DATASET_SWITCHED (not STATE_MARKED).

## Connector Language (V1)
- **V1 Default**: "Connect" feature is hidden by default (feature flag: `connectors_enabled: false`).
- **UI Copy**: Use "Upload / Add Data Source" only.
- **Future**: When `connectors_enabled: true`, show "Connect External Source" section with disabled state.

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

### Adding Data Source (Modal)
1) **Select Source**
   - Upload or select a repository-relative file path.
   - For Excel, select worksheet from a dropdown list populated offline.

2) **Validate & Preview**
   - Show first N rows in a read-only preview grid.
   - Controls: Header row toggle, column normalization (optional).

3) **Load Plan Summary**
   - Deterministic summary: dataset_id, estimated record count, detected headers, checksum, initial Review State (To Do).
   - Button labels: "Confirm Load" (primary), "Cancel" (secondary).

4) **Confirmation**
   - On confirm, copy the source file and append the LOADED event. Do not perform any Review State transition.

### Switching Data Source (Drawer)
1) **Open Data Source** from sidebar.
2) **View Active Dataset** card.
3) **Select from Saved Datasets** or click "Switch Data Source".
4) **Confirm Switch** (optional confirmation modal).
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
