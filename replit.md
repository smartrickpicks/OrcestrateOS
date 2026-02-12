# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane for defining, validating, and previewing semantic rules offline. It serves as a single source of semantic truth for authoring and reviewing semantic rules as configuration, aiming to improve operator ergonomics, streamline the patch request and review pipeline, and provide an analyst-first reference for explicit, deterministic, and auditable decisions. The system captures semantic decisions as reviewable configuration artifacts and operates offline-first, ensuring deterministic outputs using only the Python standard library for local previews.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The core design principle involves capturing semantic decisions as reviewable configuration artifacts. The system employs a canonical join strategy for data handling and a Config Pack Model with strict version matching, supporting an 11-status lifecycle for patch requests, including comment systems and role-based access control (Analyst, Verifier, Admin, Architect).

The UI features a dashboard with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are organized into six tabs: Governance, Schema & Standards, Patch Ops, People & Access, QA Runner, and Runtime Config. A Patch Studio facilitates drafting, preflight checks, and evidence packing with live previews and revision tracking. UI elements include color-coded grid highlighting, Excel-style column headers, and a PDF viewer.

Data handling supports CSV/XLSX import, inline editing, and a lock-on-commit mechanism, with a change map engine tracking cell-level changes. Workbook session caching persists uploaded Excel data to IndexedDB, supporting multi-session storage and auto-save. Triage Analytics schema matching uses normalized key comparison and `COLUMN_ALIAS_MAP` resolution.

Semantic rules generate deterministic cell-level signals on dataset load using `field_meta.json` and `qa_flags.json` for validation, populating Analyst Triage queues and driving grid coloring. Rules follow a WHEN/THEN pattern. Record identity is defined by `tenant_id`, `division_id`, `dataset_id`, `record_id`. The system uses email-based access control with Google sign-in for production OAuth.

Features include a "Contract Line Item Wizard" for batch adding and deduplication with metadata-driven validation. Export functionality generates XLSX files including all data, change logs, signals summaries, and metadata. An Audit Timeline system uses an IndexedDB-backed store for all governance actions.

A Schema Tree Editor manages the canonical rules bundle, including `field_meta.json`, `hinge_groups.json`, `sheet_order.json`, `qa_flags.json`, `document_types.json`, and `column_aliases.json`. It supports column alias resolution and tracking of schema changes. A Batch Merge feature allows combining source batches into a single governance container, with explicit rule promotion for tenant rules. Unknown Columns and Unmapped Headers tables use batch-wide condensation for display, with a "Link to Glossary" action for aliasing unknown columns.

A `SystemPass` module provides a deterministic, rerunnable, proposal-only engine for system changes. Pre-Flight triage buckets handle blockers like unknown columns or unreadable OCR. A Contract Index Engine builds a hierarchy of batch→contract→document→contract section→row, persisting summary references to SessionDB.

`UndoManager` provides local, session-scoped undo for draft-only inline edits. `RollbackEngine` creates governed rollback artifacts at four scopes (field, patch, contract, batch), capturing before/after state snapshots.

The Triage Analytics module aggregates metrics into a lightweight cache. Triage Telemetry provides live pipeline telemetry. Record Inspector Guidance provides section-specific advice. Sandbox mode is permissionless; Production uses strict role gates. A Pre-Flight Calibration Suite ensures the accuracy of pre-flight detectors. A TruthPack module with an `architect` role enables a clean-room state machine for calibration and baseline marking. A Role Registry with stable role IDs, permission-based access checks, and a People workspace are integrated. Truth Config versioning stores baselines in SessionDB with a test_mode/established lifecycle and rollback capability. An Invite system provides single-use invite creation, use, and revocation.

The system routes to triage by default for all roles. Contract-first navigation is implemented in the All Data Grid. Pre-Flight items now include section-specific tabs and human-readable labels for blockers. Grid Mode introduces inline cell editing and pending patch context tracking. A combined interstitial Data Quality Check for duplicate accounts and incomplete addresses fires automatically after workbook load. The `ADDRESS_INCOMPLETE_CANDIDATE` Matching System provides deterministic candidate matching for incomplete addresses, routing warnings and blockers to Pre-Flight.

## Modular Architecture (Phase B + C)

### AppModules Namespace (Phase C)
- `window.AppModules.Components.*` — extracted UI component modules
- `window.AppModules.Engines.*` — extracted engine modules (from Phase B)
- `window.AppModules._registry` — list of registered module paths
- `window.AppModules._version` — current extraction version (C.1.0)

### Extracted Components
| Module | Source | Container ID |
|---|---|---|
| `Components.MetricStrip` | TriageAnalytics.renderHeader batch summary | `ta-batch-summary` |
| `Components.LifecycleRail` | TriageAnalytics._renderLifecycle | `ta-lifecycle-stages` |
| `Components.ContractSummaryTable` | TriageAnalytics._renderContractTable | `ta-contract-tbody` |
| `Components.PreflightIssueTable` | renderPreflightChecklist + renderPreflightResult | `preflight-checklist` |

### Shared Engines (Phase B)
| Module | Purpose |
|---|---|
| `Engines.ContextResolver` | Normalizes patch context from any source into canonical shape |
| `Engines.PatchDraft` | Manages current patch draft lifecycle |
| `Components.PatchPanel` | Canonical patch panel for all three patch flows |

### Grid Modules (Phase D1)
| Module | Source | Delegate Target |
|---|---|---|
| `Engines.GridState` | gridState object + helpers | Grid state, column ordering, dataset, filters |
| `Components.GridHeader` | renderGrid header block | `grid-header-row` — Excel-style column headers with drag-and-drop |
| `Components.GridTable` | renderGrid body + footer | `grid-tbody`, `grid-row-count`, `grid-filter-info` — row rendering and footer |

### Record Inspector Modules (Phase D2)
| Module | Source | Delegate Target |
|---|---|---|
| `Engines.RecordInspectorState` | srrState object | Record state, field states, filters, patch draft |
| `Components.RecordInspectorHeader` | renderSingleRowReview header block | `srr-record-id`, `srr-state-badge`, `srr-title-record-name` — identity, nav, file actions |
| `Components.RecordInspectorFieldList` | renderSrrFields + filters | `srr-field-list`, `srr-field-count` — field rendering and filtering |
| `Components.RecordInspectorPatchRail` | patch panel expand/collapse/editor | Patch overlay open/close, editor render, patch list |

### PDF Viewer Modules (Phase D3)
| Module | Source | Delegate Target |
|---|---|---|
| `Engines.PdfViewerState` | srrState PDF fields + pdfMatchState | PDF URL, page, zoom, cache status, match state, persisted state |
| `Components.PdfViewerToolbar` | srrPrevPage/srrNextPage/srrZoomIn/srrZoomOut + pdfMatch* | `srr-prev-btn`, `srr-next-btn`, `srr-zoom-in`, `srr-zoom-out`, `srr-zoom-indicator`, `srr-page-indicator` — page/zoom controls and match bar |
| `Components.PdfViewerFrame` | srrLoadPdfForRecord/srrRenderPdf/srrShowEmptyState + anchor | `srr-doc-frame`, `srr-doc-container`, `srr-pdf-object`, `srr-doc-empty`, `srr-pdf-error`, `srr-pdf-match-bar` — frame rendering, load, error, anchor jump |

### Admin Panel Modules (Phase D4)
| Module | Source | Delegate Target |
|---|---|---|
| `Engines.AdminTabState` | currentAdminTab + alias map | Tab state, alias resolution, valid tab list |
| `Components.AdminTabsNav` | switchAdminTab panel/button logic | `.admin-tab`, `.admin-tab-panel` — panel show/hide, button styling, architect rail |
| `Components.AdminTabGovernance` | governance tab activation | `admin-tab-governance` — batch add toggles, batch merge refresh |
| `Components.AdminTabSchemaStandards` | standardizer tab activation | `admin-tab-standardizer` — unknown columns table refresh |
| `Components.AdminTabPatchOps` | patch-ops tab activation | `admin-tab-patch-ops` — admin queue, patch console rendering |
| `Components.AdminTabPeopleAccess` | people tab activation | `admin-tab-people` — people sub-tab restore |
| `Components.AdminTabQARunner` | qa-runner tab activation | `admin-tab-qa-runner` — QARunner tab open handler |
| `Components.AdminTabRuntimeConfig` | runtime-config tab activation | `admin-tab-runtime-config` — glossary summary render |

### Deterministic Logs
- `[APP-MODULES][P1C] registered:` — module registration
- `[APP-MODULES][P1C] bootstrap_complete` — Phase B engine registration
- `[APP-MODULES][P1D1] grid_modules_registered` — Phase D1 grid module registration
- `[APP-MODULES][P1D1] GridHeader.render` — grid header delegate render
- `[APP-MODULES][P1D2] registered:` — Phase D2 inspector module registration
- `[APP-MODULES][P1D2] inspector_modules_registered` — Phase D2 all 4 inspector modules registered
- `[APP-MODULES][P1D2] RecordInspectorHeader.renderIdentity` — header delegate render
- `[APP-MODULES][P1D3] registered:` — Phase D3 PDF viewer module registration
- `[APP-MODULES][P1D3] pdf_viewer_modules_registered` — Phase D3 all 3 PDF viewer modules registered
- `[APP-MODULES][P1D4] registered:` — Phase D4 admin module registration
- `[APP-MODULES][P1D4] admin_modules_registered` — Phase D4 all 8 admin modules registered
- `[PATCH-COMP][P1B]` — patch panel operations (open, submit, cancel, draft)

## External Dependencies
A FastAPI server acts as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF. SheetJS (XLSX) is loaded via CDN for Excel import/export functionality. The application integrates modules for:
- **P1C Contract Composite Grid**: Enhances the All Data Grid with nested, collapsible contract sections.
- **P1F Batch PDF Scan**: Adds batch-level PDF scanning for mojibake/non-searchable content.
- **P1X Canonical Contract Triage View**: Adds canonical triage metrics and contract-centric terminology.
- **P1E PDF Reliability Spike**: Diagnoses and hardens PDF anchor search reliability.
- **P1D.1 Contract Health Pre-Flight Table**: Replaces card-based grouping with a single unified nested table for contract health.
- **P1F.1 Real-Time Pre-Flight Intake**: Provides real-time visibility into batch PDF scanning.
- **P1F.2 Clean-to-SystemPass Routing**: Routes clean-scanned contracts to the System Pass queue.
- **P1G Contract Health Score**: A lifecycle-wide health scoring engine tracking contract health with a 0-100 score.
- **Data Quality Check (Combined Interstitial)**: A unified modal for duplicate account detection and incomplete address candidate matching.
- **ADDRESS_INCOMPLETE_CANDIDATE Matching System**: Deterministic candidate matching for incomplete addresses.