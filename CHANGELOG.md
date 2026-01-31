# CHANGELOG

## Version: v1.4.3
Date: 2026-01-31

### Fixed (Spreadsheet + Multi-Sheet Grid Stabilization)

- INGEST-01: Canonical Multi-Sheet Dataset Contract
  - New workbook data structure: `{ sheets: {}, order: [], activeSheet }`
  - For CSV, creates single synthetic sheet from filename
  - Deterministic lexical sheet ordering
  - activeSheet always points to valid sheet

- INGEST-02: Loader Preserves ALL Columns
  - CSV import no longer drops columns during standardization
  - Headers array includes all columns (canonical + unknown)
  - Unknown columns detected per-sheet with sample values
  - No silent column loss

- GRID-01: Grid Renders from Workbook Sheet
  - Grid reads from `workbook.sheets[activeSheet].rows` and `headers`
  - Columns dynamically determined from sheet headers
  - Empty state shows CTA to open Loader modal
  - Grid is default landing when dataLoaded=true

- GRID-02: Multi-Sheet Selector in Grid
  - Dropdown in Grid header lists `workbook.order`
  - Switching sheets updates columns/rows correctly
  - No stale columns from prior sheet

- TRIAGE-01: Triage as Alert Lens
  - Summary cards deep-link to Grid with filters: `#/grid?f=<status>`
  - navigateToGridFiltered() applies status filter deterministically

- ROW-01: Row Review Consistency
  - Row click opens Row Review from Grid and Triage consistently
  - Uses workbook-aware getGridDataset()
  - Back behavior returns to Grid with filters preserved

### Added (Debug Logging)
- [Workbook] logs on sheet add: sheet name, header count, row count
- [Grid] logs on render: activeSheet, columns.length
- [Loader] logs on import: sheets loaded, unknown column count

### Preserved
- RBAC route guards and admin isolation intact
- Loader remains modal overlay (not a route)
- No admin tools bleed into Analyst/Reviewer routes

---

## Version: v1.4.2
Date: 2026-01-31

### Added (Multi-Sheet Grid + Unknown Columns)

- Per-Sheet Mini Stats Bar
  - Row count, Ready/Needs Review/Blocked counts displayed in grid header
  - Unknown Columns count visible to Admin only
  - Stats update when sheet filter changes

- Row Virtualization for Large Datasets
  - Lazy loading kicks in for datasets > 2000 rows
  - Initial batch of 100 rows rendered, more loaded on scroll
  - Deterministic ordering preserved

- Unknown Columns Detection (Schema Drift)
  - Detects columns in data that don't match canonical schema
  - Stored in localStorage for Admin review
  - Per-sheet tracking with sample values and non-empty counts

- Admin Unknown Columns UI (under Admin > Unknown Cols tab)
  - Table showing all unknown columns with sample values
  - Actions: Add to Global Standard, Mark Source-Specific, Ignore
  - Export Update Request (copy-only JSON artifact)
  - Decisions stored in localStorage

### Preserved

- Grid is default landing when dataLoaded=true
- Triage acts as alert lens linking to Grid
- Loader remains centered modal with focus trap
- Admin UI only under #/admin/*

---

## Version: v1.4.1
Date: 2026-01-31

### Changed (Loader Modal)

- Loader UI converted from right-side drawer to centered modal overlay
  - Modal appears centered with backdrop darkening
  - ESC key closes modal
  - Click outside modal closes modal
  - X button in header closes modal
  - Focus trapped inside modal while open
  - Focus returns to trigger button on close
  - Background scroll disabled while modal open
- URL does not change when modal opens/closes (loader is not routable)
- "Continue to Grid" button replaces "Continue to Triage"
- All existing loader functionality preserved (CSV/XLSX import, sample dataset)

### Preserved

- RBAC unchanged (loader accessible as action, admin controls stay admin-only)
- Offline-first, deterministic behavior
- No new dependencies

---

## Version: v1.4.0
Date: 2026-01-31

### Added (DataDash V1 Operator Ergonomics)

- All-Data Grid Page (#/grid)
  - Dense spreadsheet-style view of standardized dataset
  - Sheet selector dropdown (multi-sheet aware, deterministic ordering)
  - Horizontal scroll with sticky header
  - Column toggle menu for visibility control
  - Search input for full-text filtering
  - Status filter chips: All, Flagged, Needs Review, Blocked, Finalized

- Deterministic Grid Filtering with Deep Links
  - Query params: f=<status>, sheet=<name>, q=<search>
  - Filter order: sheet -> status -> search
  - Sorting: severity (blocking > warning > info) -> identity triplet -> row index
  - Examples: #/grid?f=flagged, #/grid?sheet=Contracts&f=needs_review&q=sony

- Row Review Route (#/row/:id)
  - Opens record detail drawer from Grid or Triage
  - Consistent entry point for single-row review

### Changed

- Triage Converted to Alert Lens
  - Summary cards now clickable - navigate to filtered grid views
  - Click Contracts -> #/grid?f=all
  - Click Ready -> #/grid?f=ready
  - Click Needs Review -> #/grid?f=needs_review
  - Click Blocked -> #/grid?f=blocked

- Default Route Logic
  - If dataset loaded: default route is #/grid
  - If no dataset: default route is #/triage

- Sidebar Navigation
  - Added "Views" section with All-Data Grid link
  - Queues section remains for Triage alert lens

### Preserved

- RBAC route guards (admin UI only under #/admin/*)
- Loader remains drawer-only (not routable)
- Offline-first, deterministic behavior
- No new dependencies

---

## Version: v1.3.1
Date: 2026-01-31

### Changed (Pre-Staging Cleanup)

- Admin Console Tabbed Interface
  - Consolidated all admin sections into single Admin Console page with 6 tabs
  - Tabs: Governance, Config, Inspector, Standardizer, Patch Console, Evidence
  - Tab switching via switchAdminTab() function
  - Deep-linkable tabs within admin route

- Router-Level RBAC Guards
  - Role downgrade (admin -> analyst/reviewer) triggers teardownAdminState()
  - Admin state cleared when leaving admin mode
  - Toast notification on role-based redirects

- Exclusive Route Rendering
  - Each route mounts exactly one page shell
  - Admin tab panels hidden/shown, not appended
  - Verified no admin nodes in DOM when on triage

- Loader as Drawer
  - Load Data opens drawer from topbar, URL stays #/triage
  - Demo mode auto-loads sample dataset on first run

- Operator Surface Purity
  - Analyst/Reviewer see only: Triage, Patch Studio (no admin widgets)
  - Standardizer, Workflow Map, Config Inspector admin-only via tabs

### Build
- Version bumped to v1.3.1 across all pages

---

## Version: v1.3.0
Date: 2026-01-30

### Changed (UI-ADMIN-ENTITY-SEPARATION)

- Hard Page Separation
  - Fixed page visibility bug: navigateTo() now properly hides all pages (style.display='none') before showing target
  - Pages no longer "bleed through" - each route renders exactly ONE page component
  - Admin sections no longer appear appended to Triage when in Admin mode

- RBAC Route Guards
  - Non-admin users navigating to #/admin are redirected to #/triage with toast: "Admin only"
  - Non-reviewer users navigating to #/review are redirected to #/triage with toast
  - Route guards now redirect instead of silently returning

- Admin Section Markers
  - Added data-admin-section="true" attribute to all admin sections (8 sections)
  - Dev-only assertion: console.error if admin sections found in triage DOM
  - Enables automated smoke test detection of admin content in wrong context

- Page Labels
  - Updated all page headers with explicit route context (PAGE: TRIAGE, PAGE: ADMIN-GOVERNANCE, etc)
  - Build version bumped to v1.3.0 across all pages
  - PAGE: PATCH-STUDIO, PAGE: CONFIG-INSPECTOR labels added

---

## Version: v1.2.9
Date: 2026-01-30

### Added (UX Refactoring + RBAC)

- Loader Drawer
  - Converted Loader from full page to right-side drawer (460px width)
  - "Load Data" button in topbar opens drawer
  - Slide animation for smooth UX
  - CSV import with automatic standardization

- Role-Based Access Control (RBAC)
  - Admin-only content hidden from Analyst/Reviewer modes via .admin-only-content CSS
  - Debug HUD only visible to Admin role
  - Configure, Ruleset, Run Commands topbar buttons admin-only
  - Standardizer, Workflow Map, Config Inspector sections admin-only

- Navigation Flow
  - Default route changed from loader to triage
  - Demo mode auto-loads sample dataset on first run
  - Loader page deprecated (display:none !important)
  - Sidebar restructured: Load Data in DATA section with status chip

- handleCSVImport function
  - Parses CSV using parseCSV()
  - Creates standardized dataset structure
  - Saves to localStorage and upload library
  - Auto-updates UI after import

### Fixed

- setupLoaderHandlers null guards for missing DOM elements
- Consolidated duplicate parseCSV functions into single implementation (line ~3931)

---

## Version: v1.2.8
Date: 2026-01-30

### Fixed (Navigation + Routing Debug)

- Route Guard Simplified
  - Changed checkRouteRequirements to use dataLoaded flag instead of bundle check
  - More reliable routing - no longer depends on complex bundle creation
  - Added currentPage tracking variable for state machine

- Debug HUD Added
  - Fixed position HUD in top-right showing: Route, Data, Mode
  - updateDebugHUD() called on every navigation
  - Console logging for navigation attempts and route guard decisions

- Page Labels Added
  - Each page shows "PAGE: X | BUILD v1.2.8" label for deployment verification
  - Visible on Loader, Triage, Patch Studio pages

- Loader UX Updated
  - Primary CTA: Import CSV (dark panel, "Load a File")
  - Secondary CTA: Load Sample Dataset (green bar)
  - Continue panel shown when dataset is already loaded
  - Collapsible "Other Actions" for PDF attach and test utilities

- Navigation Debugging
  - Console logs for every navigateTo call with page and dataLoaded state
  - Console logs for route guard decisions

---

## Version: v1.2.7
Date: 2026-01-30

### Added (Navigation Fix + Loader UX)

- App Session State Machine
  - getAppSessionState() returns active_dataset_id, active_bundle_present, active_field_index_present
  - checkRouteRequirements() validates route requirements before rendering
  - Hard redirect: never render triage/patch/review without active_bundle_present
  - sessionStorage tracks intended route for post-load redirect

- Loader as Next Action Screen (demo-friendly)
  - Primary panel: "Dataset Ready" with Continue to Triage button when dataset active
  - Primary panel: "Demo Mode" with Load Sample Dataset button when no dataset
  - Collapsible "Other Actions" section for Import CSV, Attach PDF, Test Utilities
  - updateLoaderPageUI() shows appropriate panel based on state

- Auto-Load and Auto-Redirect
  - seedSampleDatasetOnFirstRun() seeds ds-sample into cache on first app launch
  - loadSampleDataset() auto-redirects to Triage after loading
  - importCSVFile() auto-redirects to Triage after loading
  - initLoaderPage() sets up event listeners for new Loader layout

### Changed
- Loader layout changed from 3-card menu to single primary action panel
- Route guards now check bundle presence instead of just dataLoaded flag
- navigateTo() stores intended route in sessionStorage for redirect after load

---

## Version: v1.2.6
Date: 2026-01-30

### Added (Bundle Model + Navigation Guards)

- Navigation Route Guards
  - Pages requiring dataset (triage, patch, review) redirect to loader if not loaded
  - Reset Session navigates to loader after clearing data
  - recoverNavigation() helper for stuck state recovery

- Upload Library (replaces Data Sources JSON paste)
  - List view of cached datasets with dataset_id, filename, created_at, revision
  - Actions: Activate, Duplicate as New Revision, Delete
  - localStorage persistence (STORAGE_KEY_LIBRARY)
  - Datasets saved automatically when loaded via Loader

- DatasetBundle Internal Model
  - createDatasetBundle() produces structured bundle with sheet_packets[]
  - computeFieldIndex() generates field_index from sheet_packets
  - getCurrentBundle() returns current dataset as bundle
  - Copy Bundle JSON button on Loader page

- Packager (record_id generation)
  - generateRecordId() creates stable IDs: dataset_id|sheet_name|row_number|contract_key
  - packageBundle() processes bundle into record_index with queue distribution
  - Record IDs stable across refresh for patch request attachment

### Changed
- Target Field dropdown now uses field_index from bundle (all sheet.field combinations)
- Data Sources drawer renamed to Upload Library
- resetDemoState() clears library and active dataset keys

---

## Version: v1.2.5
Date: 2026-01-30

### Added (Loader + Testability)

- Loader as First-Class Entry Point
  - New "Loader" nav item at top of sidebar under "Start" section
  - Loader page with three import options: Sample Dataset, CSV/XLSX, PDF Attachment
  - Dataset summary card shows sheets, rows, contracts, issues after load
  - "Open Spreadsheet View" CTA navigates to triage after load

- Deterministic Sample Dataset
  - In-repo sample dataset at examples/datasets/sample_v1.json
  - One-click "Load Sample Dataset" hydrates app state with contracts, catalog, royalties sheets
  - 5 sample contracts with 7 issues for testing structured intent dropdowns
  - Target Field dropdown immediately populated after loading

- Test Utilities
  - Reset Demo State: clears namespaced localStorage keys only
  - Rebuild Field Index: repopulates Target Field dropdown without reload

- CSV Import
  - Local CSV file import with delimiter inference (comma, tab, semicolon)
  - Header normalization to snake_case
  - Auto-generates contract_results from rows with contract_key
  - Note: XLSX requires export to CSV first (no external dependencies)

- PDF Attachment
  - Attach local PDFs as artifact references
  - Persists metadata (id, filename, size, timestamp, object URL)
  - PDF list displays attached files with size

### Changed
- Empty state now points to Loader instead of Data Sources drawer
- navigateTo() supports 'loader' as valid page

---

## Version: v1.2.4
Date: 2026-01-30

### Added (Structured Intent + UI Cleanup)

- Structured Intent Authoring
  - WHEN: Target Field selector (populated from dataset schema) + Condition Type dropdown
  - THEN: Action Type dropdown with structured options
  - BECAUSE: Plain-English comment field (required, max 500 chars)
  - "Other" escape hatch for edge cases with custom text input
  - Live Intent Preview showing rendered WHEN/THEN/BECAUSE

- Updated PatchRequestV1 Schema
  - intent_structured: Source of truth with target_field, condition_type, condition_params, action_type, action_params, severity, risk
  - intent_rendered: Deterministic preview string generated from intent_structured
  - Backward compatibility: legacy requests get condition_type=OTHER, action_type=OTHER

- Form Validation
  - Required fields: Target Field, Condition Type, Action Type, Comment
  - "Other" flows require custom text before submit
  - Character limit on Comment field
  - Submit disabled until validation passes

- Inline Helpers
  - Example text under selectors
  - Intent Preview updates live as user types
  - Clear error messages on validation failure

### Changed
- Removed legacy Patch Studio overlay panel (was causing stacked drawers)
- "Build Patch" button now switches to Patch Studio tab instead of opening overlay
- "Open Full Patch Studio" button removed from Patch page
- WHEN/THEN fields no longer accept arbitrary free-text (must use selectors)

### Removed
- Legacy #patch-studio overlay element
- closePatchStudio() function and related handlers

---

## Version: v1.2.3
Date: 2026-01-30

### Added (Patch Studio Integration + Role-Gated Review Pipeline)

- Role-Based Access Control
  - Three roles: Analyst, Verifier, Admin with distinct permissions
  - ROLE_PERMISSIONS configuration with can/cannot action lists
  - Verifier edit_allowlist for restricting editable fields
  - canTransition() function for role-gated status changes

- Extended 12-Status Lifecycle
  - New statuses: Needs_Clarification, Reviewer_Responded, Admin_Hold
  - STATUS_TRANSITIONS table with from/to/roles/action/audit mappings
  - Underscore naming convention for multi-word statuses
  - getAuditEventForTransition() for automatic audit event logging

- Patch Studio as Workbench Tab
  - Patch Studio integrated as a tab in Record Workbench (no stacked panels)
  - Three sub-tabs: Draft, Preflight, Evidence Pack
  - Intent fields (WHEN/THEN/BECAUSE) with structured input
  - Target Artifact and Risk Level selectors
  - Footer legend explaining Copy-only vs Submit behaviors

- Submit to Patch Queue CTA
  - "Submit to Patch Queue" button creates PatchRequest and sets status=Submitted
  - Request appears in Admin Patch Console "New" tab
  - Audit log entry appended: PATCH_REQUEST_SUBMITTED
  - Form clears after successful submission

- Preflight Checks
  - Preflight tab displays pass/warn/fail badges for validation checks
  - Checks: Intent fields populated, Evidence pack complete, Target info
  - "Run Preflight Checks" button updates check display
  - "Copy Preflight Report" copies deterministic JSON snapshot

- Evidence Pack (Copy-only)
  - Four structured evidence blocks: Observation, Expected Behavior, Rule Justification, Repro Steps
  - Individual copy buttons for each block
  - Evidence included in PatchRequest payload on Submit

- Verifier Actions
  - Request Clarification (Submitted → Needs_Clarification)
  - Analyst Response (Needs_Clarification → Reviewer_Responded)
  - Reviewer Approve (Submitted/Reviewer_Responded → Reviewer_Approved)
  - Reject with reason
  - Review Notes editable field in detail drawer

- Admin Actions Gating
  - Admin Approve (Reviewer_Approved → Admin_Approved)
  - Admin Hold / Release Hold controls
  - Export to Kiwi (copies and marks Sent_to_Kiwi)
  - Paste Kiwi Return (ingests payload, sets Kiwi_Returned)
  - Mark Applied (Kiwi_Returned → Applied)

- Revision Tracking
  - revisions array captures edits after submission
  - Each revision: revision_id, at_utc, actor, role, diff_summary, previous_snapshot
  - Revisions section in Patch Request Detail drawer (collapsible)

- Audit Log Enhancements
  - Separate audit_log array from history
  - Append-only semantics with actor, role, event, details
  - Events: PATCH_REQUEST_CREATED, PATCH_REQUEST_SUBMITTED, CLARIFICATION_REQUESTED, etc.

- Tooltips on Patch Studio Buttons
  - All action buttons have title attributes with 1-sentence descriptions
  - Legend panel explains Copy-only vs Submit behavior

### Changed
- Queue tabs updated: New shows only Submitted; Rejected includes Cancelled
- Status names use underscore format (Reviewer_Approved, Admin_Hold, etc.)
- PatchRequest schema extended with submitted_at_utc, risk, evidence, revisions, audit_log, clarification_questions, review_notes

---

## Version: v1.2.2
Date: 2026-01-30

### Added (Patch Queue as Admin Status Pipeline)
- Comment (RFI) System
  - Comment object schema with 5-status lifecycle: Open → ReviewerResponded → Resolved → ElevatedToPatchRequest/Closed
  - localStorage persistence under 'orchestrate.comments.v1'
  - CRUD functions: createComment, getComment, updateComment, resolveComment, elevateToRequest
  - Comments panel in Record Detail Drawer with Add Comment button
  - Resolve and Elevate to Patch Request actions on comments

- Patch Request Pipeline Extensions
  - Extended status lifecycle: Draft → Submitted → ReviewerApproved → AdminApproved → SentToKiwi → KiwiReturned → Applied
  - Kiwi handshake functions: markSentToKiwi, applyKiwiReturn, markApplied
  - Batch selection support with selectAllInQueue, clearPatchRequestSelection
  - Export functions: exportPatchRequestsForKiwi, exportBatchCommitPack, formatPatchRequestMarkdown

- Admin Patch Console UI
  - 7 queue tabs: New, Needs Review, Approved, Sent to Kiwi, Kiwi Returned, Applied, Rejected
  - Live count badges on each queue tab
  - Compact table with batch selection checkboxes
  - Batch actions: Export to Kiwi (Copy), Paste Kiwi Return, Mark Applied, Copy Batch Commit Pack
  - Kiwi Return Inbox modal for parsing returned JSON

- Patch Request Detail Drawer
  - Plain-English Intent display (WHEN/THEN/BECAUSE)
  - Target Artifact preview
  - Kiwi Integration section with sent/returned timestamps
  - Collapsible Kiwi Return Payload viewer
  - Apply Checklist for KiwiReturned requests
  - Context-sensitive footer actions

- Comment UI Entry Points
  - Add Comment modal with target and content fields
  - Elevate to Patch Request modal with intent fields
  - Comments section in Record Detail Drawer

### Changed
- Record Detail Drawer now includes Comments section with live updates
- Admin Status tab restructured as "Patch Console" with queue-centric navigation

---

## Version: v1.2.1
Date: 2026-01-30

### Added (Phase 2: D1-D4 Deliverables)
- D1 Masterline Autoload
  - Dev Masterline toggle in Admin panel for auto-loading master artifacts
  - Artifact Registry table showing all artifacts with status chips (Loaded/Missing/Unknown)
  - Rebind functionality for custom artifact paths
  - localStorage persistence under 'orchestrateos.artifacts.v1'
  - Refresh Status and Reload All controls

- D2 Admin Workflow Map
  - Visual vertical pipeline with 8 clickable stages
  - Each node shows: Load Data → Configuration → Standardize → Preview → Triage → Patch Draft → Evidence → PR Ready
  - Artifact status chips on relevant stages
  - Click-to-navigate to relevant panel/drawer

- D3 Standardizer JSON Canon
  - CSV input via paste or file upload
  - Delimiter inference (comma, tab, semicolon, pipe)
  - Header normalization with canonical mapping
  - merged_dataset.json deterministic output format
  - Error model: missing_required_anchor (blocking), ambiguous_columns (warning)
  - Tabbed output viewer: Summary, Dataset, Issues, Change Log
  - Generate Sample CSV for testing
  - Copy-only exports

- D4 Tooltips & Plain English
  - NOMENCLATURE labels and tooltips maps
  - Info icons (ⓘ) on table headers with hover tooltips
  - humanLabel() and getTooltip() helper functions
  - "Internal JSON (advanced)" headers on raw JSON displays
  - All user-facing text uses "Preview Packet" not "sf_packet"

### Changed
- renderTable() now adds info icons to headers with tooltips
- checkAllArtifacts() re-renders workflow map after status update
- Initialization sequence updated to load Masterline, render Workflow Map, setup Standardizer

---

## Version: v1.2.0
Date: 2026-01-30

### Added
- Viewer v1.2 Dashboard Shell Redesign (DataDash V1-style)
  - Queue-centric sidebar navigation: To Do, Needs Review, Flagged, Blocked, Finalized
  - Dynamic queue count badges that update based on contract status
  - Session management section: Data Sources, Evidence Status, Reset Session
  - Role selector: Analyst (default), Reviewer, Admin
  - Tools section: Patch Studio navigation
  - Data Sources Drawer: Right-side slide-over replacing centered modal
  - Record Drawer: Right-side slide-over for contract details with Previous/Next navigation
  - Topbar with Load Data button, session status chip, and quick actions

- First-Run Configure Wizard
  - Configure button in topbar (purple gradient)
  - First-run banner: "Using default setup. Click Configure..."
  - Multi-step wizard: Welcome, Data Sources, Workflow Defaults, Finish
  - Settings persisted to localStorage
  - Auto-setup: Repo Masters auto-load when enabled

- Admin Config Flows Panel
  - Workflow Rail: 8-step stepper (Data Sources → Export/PR)
  - Flow Stage Detail with tabs: Plain-English, Payload, Master, Diff, History
  - Admin-only access (requires Admin role)
  - Stage-specific documentation in Plain-English tab
  - Master Edit: Validate, Save Draft, Publish to Session, Revert controls
  - Diff View: Side-by-side comparison of current vs pending changes
  - History View: Timestamped log of published config changes

- Nomenclature Layer
  - Replaced "sf_packet" with "Preview Packet" in all user-facing text
  - Updated placeholders and help text with plain-English descriptions
  - Clearer error messages for data format issues

### Changed
- Replaced centered hero layout with sidebar + topbar + main workbench design
- Sidebar width: 280px fixed, with collapsible sections
- Modal → Drawer: Data Sources now slides in from right instead of centered overlay
- Removed legacy Operator role (auto-converted to Analyst on load)
- Contract table rows now open Record Drawer with full details, issues, and actions

### Technical Details
- No new dependencies or build step
- Single-file vanilla HTML+JS maintained
- All existing determinism guarantees unchanged
- Legacy 'operator' mode auto-converts to 'analyst'
- Settings stored in localStorage with versioned keys (v12)

---

## Version: v1.1.1
Date: 2026-01-30

### Added
- Viewer v1.1.1 Loader Simulation for Upload-First UX
  - Three input modes in Load Data modal: Paste JSON, Drag-and-drop file, Path hint (read-only label)
  - Session status chip in top toolbar: NOT LOADED / LOADED / FALLBACK
  - Session metadata display: source type (paste/drop/example), loaded timestamp
  - LocalStorage persistence with opt-in "Remember in this browser" toggle
  - Reset Session action that clears artifacts but preserves patch draft
  - Triage page shows active artifact source: memory(paste/drop) vs fallback(example) vs none

### Technical Details
- Product renamed to "Orchestrate OS" (internal title update)
- No external dependencies added
- Copy-to-clipboard only (no file writes)
- Deterministic sorting unchanged

---

## Version: v1.1.0
Date: 2026-01-30

### Added
- Viewer v1.1 Upload-First Flow + Modal Wizards
  - Welcome Hero: Clear "Load Data" CTA when no data is loaded
  - Data Source Modal: Select artifact path from presets or custom path
  - Ruleset Modal: Configure base config (Truth) + patch (Proposed) paths
  - Compare Modal: Load comparison artifact for delta visualization
  - Run Modal: Copy validation/preview/smoke commands to terminal
  - Triage-first landing: After loading data, user lands on Triage page by default
  - Review page hidden behind Reviewer mode toggle
  - "Build Patch" button in Workbench for contextual patching

### Changed
- Removed Run page from navigation (commands now in Run modal)
- Default route changed from #/run to #/triage
- Top toolbar appears after data is loaded with Load Data, Ruleset, Compare, Run buttons

### Technical Details
- No new dependencies or build step
- All existing determinism guarantees unchanged
- Copy-to-clipboard only (no file writes from browser)

---

## Version: v1.0.0
Date: 2026-01-30

### Added
- Viewer v1.0 Multi-Page Navigation + Mode Toggle
  - Left-nav sidebar with 4 pages: Run, Triage, Patch Studio, Review
  - Hash-based routing (#/run, #/triage, #/patch, #/review)
  - Mode toggle: Operator, Reviewer, Analyst (persisted to localStorage)
  - Run page: Toolbar, dataset paths, status summary, Stream Model as collapsible About
  - Triage page: Summary cards, filters, queues, workbench drilldown
  - Patch Studio page: Preflight Gate, Patch Draft Builder, copy outputs
  - Review page: Config+Patch Inspector, Session Loader (Comparison Mode), Evidence summary
  - Why: Improve navigation and focus by separating workflows into dedicated pages.

### Technical Details
- All existing features preserved (no regressions)
- Hash-based routing for SPA-like navigation within single HTML file
- Mode toggle changes visible emphasis (placeholder for future mode-specific visibility)
- Storage keys updated to v10

---

## Version: v0.9.0
Date: 2026-01-30

### Added
- Viewer v0.9 Session + Stream Model (Conceptual Bridge)
  - Session Timeline Panel: Models ordered sessions (ingest waves) as UI-only JSON
  - Record State Model: CONSOLIDATED | PARTIAL | WAITING | BLOCKED derived from issues
  - Never-Stop Flow Visualization: Explains open faucet concept for continuous processing
  - Reconsolidation Rules Table: Shows how partial records upgrade to consolidated
  - Copy Stream Semantics Markdown: One-click PR-ready explanation export
  - Why: Lay semantic groundwork for future streaming without runtime execution.
- docs/14_stream_semantics.md: Governance-only explanation of stream model

### Technical Details
- Record state derived deterministically from issue severity and type
- Session simulation based on loaded artifact data
- All computations performed offline in the browser
- No actual streaming, async processing, or runtime changes

---

## Version: v0.8.0
Date: 2026-01-30

### Added
- Viewer v0.8 Config + Patch Inspector (Ruleset Delta Viewer)
  - Ruleset Loader Panel: Collapsible UI to load base config + patch files
  - Patch Summary: Displays base.version, patch.base_version, author, rationale, changes_count
  - Version Match Chip: RED mismatch indicator when base_version differs
  - Changes[] Table: Deterministic table of patch changes with action, target, rule_id, when, then, severity
  - Ruleset Delta Counts: Added/Deprecated counts per target (salesforce/qa/resolver)
  - Copy Ruleset Delta Markdown: One-click export of PR-ready semantic delta description
  - Preflight Integration: Loaded config versions auto-populate Preflight Base Version Check
  - Why: Enable operators to inspect semantic ruleset changes before submitting PRs.

### Technical Details
- Deterministic change sorting: target asc, action asc, rule_id asc (nulls last), when.sheet, when.field, severity order, then fields
- All computations performed offline in the browser, no network requests
- Base + patch loaded via relative paths, no file uploads

---

## Version: v0.7.0
Date: 2026-01-30

### Added
- Viewer v0.7 Comparison Mode
  - Session Loader UI: Collapsible panel with primary and comparison artifact path inputs
  - Delta Summary Cards: Visual display of contract status changes and row-level deltas
  - Row Change Indicators: Green (added), orange (changed), red strikethrough (removed) for tables
  - Copy Delta Summary button: Export delta statistics as Markdown
  - Why: Enable operators to analyze semantic changes between artifact versions without external tools.

### Technical Details
- Join identity for change detection: `contract_key|file_url|file_name` (extended for issues/actions)
- Content hash using JSON.stringify with sorted keys for deterministic comparison
- All delta computations performed offline in the browser, no network requests

---

## Version: v0.1.0
Date: 2026-01-29

### Added
- Semantic Control Board governance documents (SCOPE_control_plane.md, CONTROL_BOARD_ARCHITECTURE.md, RULE_LIFECYCLE.md, INTERFACES.md, TRUTH_SNAPSHOT.md, CONFLICT_RESOLUTION.md, REVIEW_CHECKLIST.md, examples/README.md)
  - Why: Establish a single, auditable source of semantic truth and clear operating boundaries.
- Canonical join strategy (contract_key → file_url → file_name)
  - Why: Ensure deterministic linking across stages and prevent silent data drift.
- Determinism guarantee for previews (offline only)
  - Why: Make outcomes reproducible and reviewable without runtime dependencies or network calls.
- Operator-first index and templates (INDEX.md, rule templates, config templates)
  - Why: Streamline authoring and review, reduce ambiguity, and support consistent change control.

### Changed
- Consolidated repository as a governance-only control plane (no runtime code, no APIs, no credentials)
  - Why: Maintain a stable, reviewable semantic authority separate from execution environments.
- Local preview harness: join-triplet grouping fix (contract_key → file_url → file_name) for status aggregation and issue/action attribution
  - Why: Prevent mis-aggregation when contract_key is missing; ensure consistency across all joins.
- Local preview harness: join-failure diagnostic (blocking) when a THEN targets a missing target row (e.g., catalog)
  - Why: Surface unsafe application of rules and force BLOCKED status deterministically.
- Validator: strict base_version enforcement for patches (patch.base_version must equal base.version)
  - Why: Prevent drift and ensure patches apply to the intended base semantics.

### Deprecated
- None in this initial version
  - Why: First release of governance materials; no prior artifacts to deprecate.

---

## Version: v0.1.1
Date: 2026-01-29

### Added
- docs/07_replit_mcp.md and scripts/mcp_link_gen.py (deterministic ENCODED/LINK/BADGE_MARKDOWN output)
  - Why: Enable safe, reproducible MCP setup in Replit without secrets.
- scripts/replit_smoke.sh strict diff gate (with `--allow-diff` override)
  - Why: Provide a clear pass/fail operator signal and reproducible verification.

### Changed
- README.md and docs/INDEX.md updated to include Replit MCP and smoke flow
  - Why: Improve discoverability and reduce operator onboarding time.

### Verification
- Replit golden run verified — see docs/replit_baseline.md (records date/time, environment, and SHA256 of out/sf_packet.preview.json).

### Deprecated
- None
  - Why: Non-breaking governance-surface enhancements only.

---

## Version: v0.1.2
Date: 2026-01-30

### Changed
- Determinism hardening in preview outputs: explicit array sorting by join triplet (contract_key → file_url → file_name) and normalized key ordering for diffing.
  - Why: Eliminate incidental ordering diffs; ensure stable, audit-friendly previews.
- Documentation updates:
  - TRUTH_SNAPSHOT: clarified authoritative vs illustrative files and config-driven semantics.
  - replit_baseline: added narrative of determinism fix and authority of smoke tests over editor diagnostics.

### Notes
- No semantic rule changes. Configuration meaning is unchanged; this release only enforces ordering/normalization for deterministic previews.

### Required Operator Action
- Treat v0.1.2 as the locked baseline. Future changes require a version bump and strict smoke pass (baseline and, when applicable, edge-case packs).

---

## Version: v0.1.3 (DRAFT)
Date: 2026-01-30

### Added
- Patch: config/config_pack.v0.1.3.patch.json (SF_R2_ARTIST_REQUIRES_ARTIST_NAME — warning completeness rule)

### Changed
- examples/expected_outputs/sf_packet.example.json updated to reflect new rule (artist row Needs Review)

### Why
- Low-risk, demonstrable rule aligned with subtype expectations. Determinism unaffected.

### Smoke Evidence
- Baseline smoke should pass with updated expected output.

---

## Meta: Product Rename (2026-01-30)
- Changed: Product name to “Orchestrate OS.”
- Why: Unify naming; semantics unchanged. Historical aliases (Kiwi, Control Board, Kiwi Semantic Control Board) remain as searchable references.