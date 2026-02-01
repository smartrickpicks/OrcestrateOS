# Load Data View — Governed Loader UX (Modal)

Contract: This document defines the governed, offline-first Loader experience. It specifies UI placement, allowed inputs, deterministic behaviors, audit requirements, and role semantics. It does not define implementation code or runtime ingestion services.

## Placement & Access
- Entry: Sidebar item "Load Data". Selecting it opens a modal dialog; no full-screen route.
- Modal: blocks background interaction until dismissed; ESC to close.
- Roles: Analysts and Admins may initiate loads. Verifiers may view the modal in read-only preview mode.

## Supported Inputs & Parity
- Accepted file types: CSV and Excel (.xlsx).
- Parity statement:
  - CSV and Excel receive identical validation and mapping flows.
  - For Excel, each worksheet is treated as a logical dataset; the user selects one worksheet per load operation.
  - No formula evaluation; values are treated as static cell contents.

## Copy-Only Ingestion
- The loader performs copy-only ingestion: source files are copied into repository-bound storage (e.g., under a data or docs-adjacent directory) without mutation.
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
Upon successful confirmation, the loader must emit exactly one LOADED event per dataset with payload fields:
- file_path (repository-relative)
- file_format (csv | xlsx)
- sheet_name (xlsx only; otherwise null)
- row_count, column_count
- headers (array of strings)
- source_checksum (hex digest of source file bytes)

Additionally, the view must emit one VIEWED event when the modal is opened (context: "record" or "dataset") for traceability.

## User Flow (Modal)
1) Select Source
- Upload or select a repository-relative file path.
- For Excel, select worksheet from a dropdown list populated offline.

2) Validate & Preview
- Show first N rows in a read-only preview grid.
- Controls:
  - Header row toggle (Has header row / No header row).
  - Column normalization (optional, opt-in) with a non-destructive preview.

3) Mapping (Optional)
- Read-only display of proposed field names and types; no irreversible transformations.

4) Load Plan Summary
- Deterministic summary: dataset_id, estimated record count, detected headers, checksum, and initial review state (To Do).
- Button labels: "Confirm Load" (primary), "Cancel" (secondary).

5) Confirmation
- On confirm, copy the source file into the repository location and append the LOADED event. Do not perform any review state transition.

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
