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
  - Two-column row: Upload tile (left) | Connect tile (right, disabled V2)
  - Demo Dataset load button
- **Affordances**: Upload CSV/XLSX, load demo dataset.

### State B: Active Dataset
- **Condition**: Active dataset loaded.
- **Display**: Right-side panel with (in order):
  1. Active Dataset card with name, row count, loaded timestamp, "ACTIVE ▾" badge
  2. Two-column row: Upload New tile (left) | Connect tile (right, disabled V2)
  3. Search stub (V2) — placeholder, shows toast on input
  4. Saved Datasets list (if any exist)
- ACTIVE badge has click menu with "Disconnect" action.

### Saved Datasets

- Actions (per Saved dataset):
  - Activate — set as Active (rotates current Active to Saved)
  - Duplicate — create a copy under Saved
  - Delete — permanently remove (disabled for Active; only enabled for Saved)
- Constraints:
  - Delete is disabled when dataset is Active; use Disconnect first
  - Activate preserves Review States and evidence (context switch only)
- Upload helper text: "Uploading rotates current active dataset to Saved."
- **Affordances**: View metadata, disconnect, upload new, search (stub), select from Saved.

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

## Panel Search Stub (V2)
- **Location**: Between Upload|Connect row and Saved Datasets section.
- **Placeholder**: "Search agreements, accounts, record IDs..."
- **Behavior**: On input or Enter, show "Search coming soon (V2)" toast.
- **V2 badge**: Visible next to "Search" label.
- **No filtering**: Stub only, no actual search logic.

## Source Types

### V1: Local Upload (Implemented)
- **Status**: Available
- **Behavior**: Direct upload via Data Source panel drop zone
- **Supported formats**: CSV, XLSX (multi-contract-section)
- **Offline-compatible**: Yes (SheetJS library loaded from CDN, cached)
- **Parser entrypoint**: `parseWorkbook(arrayBuffer, filename)` for reuse in V1.5 Drive integration

### Download Once, Work Locally (v1.4.13)
Data sources follow a "copy-in" model:
- **Ingestion**: Files are parsed and stored in IndexedDB/localStorage
- **PDF Caching**: Network PDFs are cached locally (25 MB per file, 250 MB total)
- **Offline Work**: After initial load, records can be reviewed offline
- **No Background Sync**: Changes are local-only until explicit export

This design ensures analysts can work on flights, in low-connectivity environments, or with sensitive data that shouldn't leave the device.

### V1.5 Connectors (Copy-In Stubs)
> **Note:** These are governance stubs for future copy-in connectors. No runtime integration exists yet.

#### Google Drive Connector (V1.5 Stub)
- **Status**: Not implemented
- **Purpose**: One-time copy-in from Drive folder (not sync)
- **Behavior**: Download files once, then work locally
- **Requires**: OAuth, Drive API read access

### CSV Ingestion (v1.4.12)
- Single contract section workbook created from CSV file
- Contract section name derived from filename (without extension)
- Delimiter auto-detected (comma, tab, semicolon, pipe)
- Column mapping applied for file_name/file_url (see below)

### XLSX Ingestion (v1.4.12)
- Multi-contract-section workbook support via SheetJS library
- Contract section names from Excel workbook
- Contract section selector populated with all contract section names (lexically sorted)
- Switching contract sections updates Grid and Triage context

### Column Mapping Rules (v1.4.12)
Per-row `file_name` and `file_url` are resolved for Record Inspection PDF viewer:

1. **Primary (explicit headers)**: Case-insensitive match for:
   - `file_name`, `filename`, `file name` → maps to `file_name`
   - `file_url`, `fileurl`, `file url`, `url` → maps to `file_url`

2. **Fallback (DataDash-style)**: If explicit headers not found:
   - Column A (first column) → treated as `file_name`
   - Column B (second column) → treated as `file_url`

3. **Missing columns**: If mapping cannot be resolved:
   - Warning banner shown in Data Source panel: "Missing required columns: file_name/file_url"
   - Record Inspection shows empty PDF state with guidance

Column mapping is persisted in session state (not source bytes).

### V2 Stubs (Not Implemented)

> **Note:** The following are governance stubs only. No runtime integration exists.

#### Google Drive Drop (V2 Stub)
- **Status**: Not implemented
- **Purpose**: Auto-ingest from shared Drive folder
- **Requires**: OAuth integration, folder watch API
- **UI Placeholder**: Disabled tile with "V2" badge

#### Dropbox Drop (V2 Stub)
- **Status**: Not implemented
- **Purpose**: Auto-ingest from Dropbox folder
- **Requires**: Dropbox API integration
- **UI Placeholder**: Disabled tile with "V2" badge

#### Email Drop (V2 Stub)
- **Status**: Not implemented
- **Purpose**: Ingest attachments from dedicated mailbox
- **Requires**: IMAP/SMTP integration, attachment extraction
- **UI Placeholder**: Disabled tile with "V2" badge

## Attribution and Routing (Docs-Only)

### Attribution Display
When a dataset is loaded, the Data Source panel shows:
- **Source**: Origin path or method (e.g., "inbound/contracts.xlsx")
- **Submitter**: Resolved identity (if available) or "Unknown"
- **Loaded at**: Timestamp of ingestion
- **Checksum**: SHA-256 of source file (collapsed by default)

### Attribution Methods
| Method | Description | Status |
|--------|-------------|--------|
| Folder name | Per-user subfolder in inbound/ | V1 available |
| Manifest | manifest.json with explicit submitter field | V1 available |
| Auth token | Identity from authenticated session | V2 stub |

### Routing Display
After ingestion, the panel shows routing summary:
- **Records routed**: Count of records assigned to Review States
- **Initial state distribution**: e.g., "42 To Do, 3 Blocked"
- **Assigned pool**: "Analyst pool" (default)

### Routing Rules Reference
See docs/ingestion/INGESTION_DOCTRINE.md for complete routing logic.

## Connector Language (V1)
- **V1 Default**: Connect stubs are always visible but disabled (in Connect tile).
- **Connect tile** shows: "Connect Source — Google Drive, MCP" with V2 badge.
- **V2 buttons** (disabled):
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

### Ingestion Events (V1)
The Data Source view emits the following ingestion events:
- INGESTION_REGISTERED: When file is accepted into inbound folder with checksum
- SUBMISSION_ATTRIBUTED: When submitter identity is resolved
- ROUTED_TO_ANALYST: When records are assigned initial Review States

See docs/AUDIT_LOG.md for complete event type definitions and payload contracts.

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
