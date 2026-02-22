# Data Loader & Ingestion Pipeline

Audience: Developers, operators, and future agents working on data ingestion
Purpose: Document how Excel files are uploaded, parsed, cached, restored, and processed through the signal engine — and what's planned for Google Drive integration and evolving data standards
Scope: End-to-end data pipeline from file selection to grid rendering
Authority Level: Reference documentation; implementation must conform
Owner: Orchestrate OS engineering
Last Updated: 2026-02-08

---

## Table of Contents

1. [Overview](#overview)
2. [Pipeline Stages](#pipeline-stages)
3. [Stage 1: File Selection & Upload](#stage-1-file-selection--upload)
4. [Stage 2: Parsing (SheetJS)](#stage-2-parsing-sheetjs)
5. [Stage 3: Workbook Population](#stage-3-workbook-population)
6. [Stage 4: Signal Generation](#stage-4-signal-generation)
7. [Stage 5: Triage Queue Population](#stage-5-triage-queue-population)
8. [Stage 6: Grid Rendering](#stage-6-grid-rendering)
9. [Caching & Storage Architecture](#caching--storage-architecture)
10. [Session Management](#session-management)
11. [Auto-Save Mechanism](#auto-save-mechanism)
12. [Session Restore on Page Load](#session-restore-on-page-load)
13. [Saved Sessions (Multi-Session Support)](#saved-sessions-multi-session-support)
14. [Data Source View UX](#data-source-view-ux)
15. [Future: Google Drive Integration](#future-google-drive-integration)
16. [Future: Evolving Data Standards](#future-evolving-data-standards)
17. [Key Files & Functions Reference](#key-files--functions-reference)
18. [Related Documentation](#related-documentation)

---

## Overview

Orchestrate OS is an offline-first, browser-based semantic control board. Data enters the system via Excel file upload (.xlsx/.xls) or CSV. There is no server-side ingestion — everything runs in the browser using SheetJS for parsing and IndexedDB for persistence.

The pipeline follows a deterministic, linear flow:

```
File Upload → Parse (SheetJS) → Workbook Population → Signal Generation → Triage Queues → Grid Rendering
                                       ↓
                              Cache to IndexedDB (auto-save every 3s)
                                       ↓
                              Session Restore on next page load
```

No external services are required. The Python/FastAPI backend (`server/pdf_proxy.py`) is only used for CORS-safe PDF fetching and text extraction — it has no role in Excel ingestion.

---

## Pipeline Stages

### Stage 1: File Selection & Upload

**Entry points** (two UI locations):

1. **Sidebar "Upload Excel" button** — Always visible in the sidebar. Triggers a hidden `<input type="file">` element (`#excel-file-import`).
2. **Data Source drawer "Upload Excel" button** — Inside the right-side Data Source panel, triggered by `#drawer-excel-file-input`.

Both call the same handler:

```
handleExcelUpload(input)
  → validates file extension (.xlsx or .xls)
  → calls handleFileImport(file)
  → resets the <input> for future uploads
```

**File**: `ui/viewer/index.html`, function `handleExcelUpload` (~line 20921)

**Accepted formats**: `.xlsx`, `.xls`, `.csv`

**What happens on upload**:
- A loading overlay appears ("Processing {filename}...")
- All cell-level caches are cleared (`clearAllCellStores()`) to prevent stale highlights from a previous dataset
- A `FileReader` reads the file as an `ArrayBuffer` (for Excel) or text (for CSV)

---

### Stage 2: Parsing (SheetJS)

The core parsing function is `parseWorkbook(data, filename)`.

**Library**: SheetJS (XLSX) v0.20.1, loaded via CDN:
```html
<script src="https://cdn.sheetjs.com/xlsx-0.20.1/package/dist/xlsx.full.min.js"></script>
```

**For XLSX/XLS files**:
1. `XLSX.read(arrayBuffer, { type: 'array' })` parses the binary Excel data
2. Iterates over `workbookXLSX.SheetNames` — each sheet is processed independently
3. `XLSX.utils.sheet_to_json(sheet, { header: 1, defval: '' })` converts each sheet to a 2D array
4. First row becomes headers (trimmed strings)
5. Remaining rows become objects keyed by header names
6. Empty rows (all cells blank/null/whitespace) are skipped
7. Column mapping is resolved per-sheet via `resolveColumnMapping(headers)` and applied via `applyColumnMapping()`

**For CSV files**:
1. Raw text is parsed by `parseCSV(text)` with delimiter inference
2. Single sheet created, named after the file (minus extension)
3. Same column mapping flow applies

**Output**: A result object:
```javascript
{
  sheets: {
    "SheetName": {
      headers: ["col1", "col2", ...],
      rows: [{ col1: "val", col2: "val", ... }, ...],
      meta: { sheetIndex: 0, mapping: {...} }
    }
  },
  order: ["Sheet1", "Sheet2", ...],  // sorted alphabetically
  errors: [],
  mapping: { ... }  // first sheet's mapping (legacy compat)
}
```

**File**: `ui/viewer/index.html`, function `parseWorkbook` (~line 6481)

---

### Stage 3: Workbook Population

After parsing, the in-memory workbook is populated:

```javascript
var workbook = {
  sheets: {},       // { sheetName: { headers: [], rows: [], meta: {} } }
  order: [],        // Deterministic sheet ordering
  activeSheet: null // Currently selected sheet
};
```

**Population flow** (inside `handleFileImport`):
1. `resetWorkbook()` — clears all existing data
2. For each sheet in parse result, `addSheet(sheetName, headers, rows, meta)` is called
3. `gridState.sheet` is validated — if the previously selected sheet doesn't exist in the new workbook, it resets to the first sheet
4. `allData` is populated for legacy compatibility (flat array of all rows across sheets)
5. Data is saved to `localStorage` under `STORAGE_KEY_DATASET`
6. File is saved to the Upload Library via `saveToUploadLibrary()`

**Post-population steps** (in order):
- `dataLoaded = true`
- `updateUIForDataState()` — shows/hides empty state vs data views
- `populateSubtypeDropdown()` — populates contract section filter dropdown
- `populateGridSheetSelector()` — populates grid contract section tabs
- `renderAllTables()` — renders legacy tables
- `renderGrid()` — renders the main All-Data Grid
- `persistAllRecordsToStore()` — saves all records to the Canonical Record Store (localStorage) for Record Inspection rehydration
- `generateSignalsForDataset()` — runs the signal engine (next stage)
- `seedPatchRequestsFromMetaSheet()` — seeds patch requests from RFI meta sections if present

**File**: `ui/viewer/index.html`, function `handleFileImport` (~line 20951)

---

### Stage 4: Signal Generation

The signal engine runs deterministically on every cell of every record after data load.

**Function**: `generateSignalsForDataset()` (~line 13991)

**Inputs**:
- `workbook.sheets` — all loaded data
- `rulesBundleCache` — preloaded rules from `/rules/rules_bundle/`:
  - `field_meta.json` (442 fields) — field definitions, types, required flags, picklist options
  - `qa_flags.json` (3 flags) — QA validation flag definitions
  - `hinge_groups.json` (47 hinges) — primary/secondary decision fields
  - `sheet_order.json` (8 contract sections) — canonical contract section ordering

**Signal types generated**:

| Signal | Severity | Source | Trigger |
|--------|----------|--------|---------|
| `MISSING_REQUIRED` | error | `field_meta.json` | Required field is blank/empty |
| `PICKLIST_INVALID` | warning | `field_meta.json` | Value not in allowed picklist options |
| `MOJIBAKE_DETECTED` | warning | encoding_check | Text contains encoding artifacts |
| `QA_FLAG` | info | `qa_flags.json` | Informational flags (non-duplicate with above) |

**Process**:
1. Resets `signalStore.signals_by_cell` and stats
2. Iterates all contract sections → all rows → all non-internal fields (fields not starting with `_`)
3. For each cell, `generateCellSignals(row, fieldKey, sheetName, recordId)` produces signals
4. Signals are stored in `signalStore.signals_by_cell[recordId][fieldKey]`
5. Stats are aggregated by type
6. After all signals generated, triage queues are populated

**Output**: `signalStore` populated with cell-level signals, driving grid coloring and triage queues.

---

### Stage 5: Triage Queue Population

Signals are routed into four Analyst Triage queues:

| Queue | Signal Filter |
|-------|---------------|
| **Manual Review** | `MOJIBAKE_DETECTED` + `MISSING_REQUIRED` + `PICKLIST_INVALID` signals, plus items seeded from `RFIs & Analyst Notes` meta section (Note Type = "Manual Review") |
| **Salesforce Logic Flags** | `QA_FLAG` with ERROR or WARNING severity |
| **Patch Requests** | Actual patch requests only (RFIs, corrections); seeded from `RFIs & Analyst Notes` meta section; sorted by `updated_at` descending |
| **System Changes** | `QA_FLAG` with INFO severity, plus items seeded from `*_change_log` sections |

Queue counts appear in the sidebar Progress card (TO DO / REVIEW / DONE) and in the Triage view.

---

### Stage 6: Grid Rendering

The All-Data Grid renders records with:
- **Status-colored rows** using `STATUS_COLOR_MAP` (ready=green, needs_review=orange, blocked=red, finalized=blue, flagged=purple)
- **Signal-driven cell highlighting** based on `signalStore`
- **Contract section tabs** for multi-contract-section navigation
- **Filter bar** for status filtering (All, Ready, Needs Review, Blocked)
- **Search** across all fields
- **Column visibility** controls via Columns button

---

## Caching & Storage Architecture

### IndexedDB (Primary — v1.6.56+)

The `SessionDB` module manages all persistent storage:

**Database**: `orchestrate_sessions` (version 1)

**Object Stores**:

| Store | Key | Purpose |
|-------|-----|---------|
| `workbook_cache` | `'active_workbook'` | Active workbook data (sheets, order, activeSheet, datasetId, filename, timestamp) |
| `saved_sessions` | session `id` | Named saved sessions (up to 10) |

**Why IndexedDB?** Workbook data can easily exceed localStorage's ~5MB limit. IndexedDB has no practical size limit and handles structured cloning efficiently.

**Pointer system**: A small JSON pointer is stored in `localStorage` at `orchestrate_idb_workbook_ptr` to indicate that IndexedDB contains cached data. This allows fast "is there cached data?" checks without opening IndexedDB.

### localStorage (Fallback)

If IndexedDB is unavailable or fails:
- Workbook cache falls back to `orchestrate_workbook_cache` key
- Saved sessions fall back to `orchestrate_saved_sessions` key
- A migration system (`SessionDB.migrateFromLocalStorage()`) moves old localStorage data to IndexedDB on first load

### Other localStorage Keys

| Key | Purpose |
|-----|---------|
| `orchestrate_dataset` | Raw dataset + column mapping (legacy) |
| `orchestrate_nav_state` | Current page, sheet, scroll position |
| `orchestrate_idb_sessions_idx` | Index of saved session metadata (for fast listing) |

### Canonical Record Store

Separate from the workbook cache, `persistAllRecordsToStore()` saves each record individually to localStorage keyed by `record_id`. This enables Record Inspection to rehydrate individual records without loading the entire workbook.

---

## Session Management

### Auto-Save Mechanism

**Function**: `scheduleAutosave()` (~line 6710)

- Runs on a 3-second interval via `setTimeout` (not `setInterval`)
- Each tick saves:
  - Workbook data to IndexedDB via `saveWorkbookToCache()`
  - Navigation state to localStorage via `saveNavStateToCache()`
- Only saves if workbook has data (`workbook.order.length > 0`)
- Reschedules itself after each save (self-chaining)
- Started automatically after data load and session restore

**What is saved**:
```javascript
{
  workbook: {
    sheets: workbook.sheets,     // All sheet data (headers + rows + meta)
    order: workbook.order,       // Sheet ordering
    activeSheet: workbook.activeSheet
  },
  datasetId: IDENTITY_CONTEXT.dataset_id,
  filename: "...",               // Display name
  savedAt: "2026-02-08T..."     // ISO timestamp
}
```

### Session Restore on Page Load

**Function**: `masterlineAutoload()` (~line 6722)

On every page load:
1. `loadWorkbookFromCache()` checks IndexedDB first, then localStorage fallback
2. If cached data found:
   - Workbook is rehydrated (`workbook.sheets`, `workbook.order`, `workbook.activeSheet`)
   - UI is updated (data source bar, grid, tables)
   - Signals are regenerated (`generateSignalsForDataset()`)
   - Triage queues are reseeded
   - Navigation state is restored (page, sheet, scroll position)
   - Auto-save timer is restarted
3. If no cache: empty state shown, user prompted to upload

**Staged Loader UI**: During restore, a staged loading overlay shows progress:
- Stage 1: "Loading..." (reading from IndexedDB)
- Stage 2: "Standardizing..." (populating workbook)
- Stage 3: "Validating..." (running signal engine)
- Stage 4: Complete (overlay dismissed)

### Saved Sessions (Multi-Session Support)

Users can save up to **10 named sessions**:

- **Save**: `saveCurrentSession(name)` stores the full workbook + metadata to IndexedDB
- **Load**: `loadSavedSession(id)` replaces the active workbook with a saved session
- **Delete**: Individual sessions can be removed
- **List**: `getSavedSessions()` returns the session index from localStorage

Sessions appear in the Data Source drawer under "Saved Datasets" with name, row count, and timestamp.

**Storage**: Each session is stored in the `saved_sessions` object store with its own unique ID. The session index (lightweight metadata) is kept in localStorage at `orchestrate_idb_sessions_idx` for fast listing without opening IndexedDB.

---

## Data Source View UX

The Data Source view is defined in `docs/ui/views/data_source_view.md`.

**Key states**:
- **No Data (Empty State)**: Upload tile + Connect tile (disabled, V2) + Demo Dataset button
- **Active Dataset**: Active Dataset card + Upload New + Connect (disabled) + Saved Datasets list

**Upload behavior**: Uploading a new file rotates the current active dataset to "Saved" (if auto-save is enabled).

**Roles**:
- Analysts and Admins: Can upload and switch data sources
- Verifiers: Read-only preview mode

---

## Future: Google Drive Integration

**Status**: Planned for V2. Currently represented by a disabled "Connect" tile in the Data Source view.

**Design intent** (from `data_source_view.md`):
- The Connect tile will enable linking to external data sources, starting with Google Drive
- Google OAuth is already stubbed for production authentication (sign-in page has Google OAuth button)
- The connection flow would:
  1. Authenticate via Google OAuth
  2. Browse/select an XLSX or CSV file from Google Drive
  3. Download the file contents to the browser
  4. Feed it through the same `parseWorkbook()` pipeline (no backend needed)
  5. Optionally sync changes back (write-back is a future consideration)

**What needs to be built**:
- Google Drive API integration (file picker, download)
- OAuth token management (refresh tokens, scopes)
- Connection state persistence (which Drive file is linked)
- Sync indicator (last synced timestamp, manual refresh button)
- Conflict resolution if the Drive file changes while edits are in progress locally

**What stays the same**:
- The entire parsing, workbook population, signal generation, and caching pipeline remains unchanged
- Google Drive is just another file source — once the bytes are in the browser, the same `parseWorkbook()` function handles everything
- IndexedDB caching continues to work identically

---

## Future: Evolving Data Standards

As the data standard evolves, these are the key areas that need updating:

### Rules Bundle Updates

When fields are added, renamed, or removed:
1. Update `rules/rules_bundle/field_meta.json` — add/modify field definitions, types, required flags, picklist options
2. Update `rules/rules_bundle/hinge_groups.json` — if hinge fields change
3. Update `rules/rules_bundle/sheet_order.json` — if contract sections are added/renamed/reordered
4. Regenerate rules bundle (NOTE: `scripts/build_rules_bundle.py` not found in repo — edit JSON files directly or use Schema Tree Editor in Admin panel)
5. Validate against schemas in `rules/rules_bundle/schemas/`

### Column Mapping Updates

The `resolveColumnMapping()` function maps incoming Excel column headers to canonical field names. When column names change:
1. Update the mapping rules in `resolveColumnMapping()` to handle new/renamed columns
2. Update `applyColumnMapping()` if transformation logic changes
3. Test with a sample file to verify all columns are recognized

### Signal Engine Updates

If new validation rules are needed:
1. Add new signal types to the `generateCellSignals()` function
2. Register them in the signal type registry (severity, source)
3. Route them to the appropriate triage queue
4. Update grid coloring if new signal types need distinct colors

### Document Type Updates

New document types are added to `config/document_types.json` and loaded on startup via the rules bundle loader.

### Config Pack Updates

The Config Pack Model (`config_pack.base.json` for baseline, `config_pack.patch.json` for changes) may need version bumps when the standard changes. Strict version matching is enforced.

---

## Key Files & Functions Reference

### Primary Source File

| File | Role |
|------|------|
| `ui/viewer/index.html` | Single-file application containing all JS, HTML, and CSS |

### Key Functions (by pipeline stage)

| Function | Location (approx. line) | Purpose |
|----------|------------------------|---------|
| `handleExcelUpload(input)` | ~20921 | Entry point for Excel file selection |
| `handleFileImport(file)` | ~20951 | Unified file import handler (CSV + XLSX) |
| `parseWorkbook(data, filename)` | ~6481 | Core parser using SheetJS |
| `resolveColumnMapping(headers)` | (search for function) | Maps Excel columns to canonical names |
| `applyColumnMapping(rows, headers, mapping)` | (search for function) | Applies column name normalization |
| `resetWorkbook()` | ~6101 | Clears in-memory workbook |
| `addSheet(sheetName, headers, rows, meta)` | ~6372 | Adds a parsed sheet to the workbook |
| `generateSignalsForDataset()` | ~13991 | Runs signal engine over all cells |
| `generateCellSignals(row, fieldKey, sheetName, recordId)` | (search for function) | Per-cell signal generator |
| `persistAllRecordsToStore()` | ~5752 | Saves records to Canonical Record Store |
| `saveWorkbookToCache()` | ~6111 | Saves workbook to IndexedDB |
| `loadWorkbookFromCache()` | ~6135 | Loads workbook from IndexedDB/localStorage |
| `clearWorkbookCache()` | ~6158 | Clears all cached workbook data |
| `scheduleAutosave()` | ~6710 | Starts the 3-second auto-save timer |
| `masterlineAutoload()` | ~6722 | Session restore on page load |
| `restoreSessionFromStorage()` | ~10134 | Legacy session restore (JSON artifacts) |
| `saveCurrentSession(name)` | (search for function) | Saves named session to IndexedDB |
| `renderGrid()` | (search for function) | Renders the All-Data Grid |
| `seedPatchRequestsFromMetaSheet()` | (search for function) | Seeds patch requests from meta sections |

### Storage Module

| Module | Location (approx. line) | Purpose |
|--------|------------------------|---------|
| `SessionDB` | ~4556 | IndexedDB wrapper for workbook + session storage |
| `AuditTimeline` | ~4818 | IndexedDB wrapper for audit event storage |

### Configuration Files

| File | Purpose |
|------|---------|
| `rules/rules_bundle/field_meta.json` | Field definitions, types, validation rules (442 fields) |
| `rules/rules_bundle/hinge_groups.json` | Hinge field classifications (47 hinges) |
| `rules/rules_bundle/sheet_order.json` | Canonical contract section ordering (8 contract sections) |
| `rules/rules_bundle/qa_flags.json` | QA flag definitions (3 flags) |
| `config/document_types.json` | Document type definitions (5 types) |
| `config/config_pack.base.json` | Baseline configuration |
| `config/config_pack.example.patch.json` | Example patch configuration |

### External Dependencies

| Dependency | Version | Loaded Via | Purpose |
|------------|---------|------------|---------|
| SheetJS (XLSX) | 0.20.1 | CDN script tag | Excel/CSV parsing |

No other external dependencies. The rest of the application uses only browser-native APIs (IndexedDB, localStorage, FileReader, etc.).

---

## Related Documentation

| Document | Path | Relevance |
|----------|------|-----------|
| Data Source View | `docs/ui/views/data_source_view.md` | UX contract for the upload/connect interface |
| Ingestion Doctrine | `docs/ingestion/INGESTION_DOCTRINE.md` | Folder conventions and attribution patterns |
| Rules Bundle | `docs/rules/rules_bundle.md` | How semantic rules are structured and regenerated |
| All-Data Grid View | `docs/ui/views/all_data_grid_view.md` | Grid rendering and interaction patterns |
| Record Inspection View | `docs/ui/views/record_inspection_view.md` | Record Inspection and field inspection |
| Triage View | `docs/ui/views/triage_view.md` | Triage queue structure and routing |
| Audit Log | `docs/AUDIT_LOG.md` | Audit timeline system (IndexedDB-backed) |
| UI Principles | `docs/ui/ui_principles.md` | General UI/UX governance rules |
| V1 Flow Doctrine | `docs/V1/Flow-Doctrine.md` | V1 workflow and lifecycle rules |

---

## Appendix: Pipeline Sequence Diagram

```
User clicks "Upload Excel"
    │
    ▼
handleExcelUpload(input)
    │  validates .xlsx/.xls extension
    ▼
handleFileImport(file)
    │  shows loading overlay
    │  clears cell caches
    │  reads file via FileReader
    ▼
parseWorkbook(data, filename)
    │  SheetJS: XLSX.read() → sheet_to_json()
    │  resolveColumnMapping() per sheet
    │  applyColumnMapping() per sheet
    │  returns { sheets, order, errors, mapping }
    ▼
Workbook Population
    │  resetWorkbook()
    │  addSheet() for each parsed sheet
    │  populate allData (legacy compat)
    │  save to localStorage
    │  saveToUploadLibrary()
    ▼
Post-Load Processing
    │  persistAllRecordsToStore() → Canonical Record Store
    │  generateSignalsForDataset() → Signal Engine
    │  seedPatchRequestsFromMetaSheet() → Patch Requests
    ▼
UI Rendering
    │  renderGrid() → All-Data Grid with status colors + signal highlights
    │  populateSubtypeDropdown() → Contract section filter
    │  renderAllTables() → Legacy tables
    │  updateUIForDataState() → Show data views, hide empty state
    ▼
Auto-Save Started
    │  scheduleAutosave() → saves to IndexedDB every 3 seconds
    ▼
Ready for Analyst Work
    (Triage, Field Inspection, Patch Authoring, etc.)
```
