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

A Schema Tree Editor manages the canonical rules bundle, including `field_meta.json`, `hinge_groups.json`, `sheet_order.json`, `qa_flags.json`, `document_types.json`, and `column_aliases.json`. It supports column alias resolution and tracking of schema changes. A Batch Merge feature allows combining source batches into a single governance container, with explicit rule promotion for tenant rules.

A `SystemPass` module provides a deterministic, rerunnable, proposal-only engine for system changes. Pre-Flight triage buckets handle blockers like unknown columns or unreadable OCR. A Contract Index Engine builds a hierarchy of batch, contract, document, contract section, row, persisting summary references to SessionDB.

`UndoManager` provides local, session-scoped undo for draft-only inline edits. `RollbackEngine` creates governed rollback artifacts at four scopes (field, patch, contract, batch), capturing before/after state snapshots.

The Triage Analytics module aggregates metrics into a lightweight cache. Record Inspector Guidance provides section-specific advice. Sandbox mode is permissionless; Production uses strict role gates. A TruthPack module with an `architect` role enables a clean-room state machine for calibration and baseline marking. A Role Registry with stable role IDs, permission-based access checks, and a People workspace are integrated.

The system routes to triage by default for all roles. Contract-first navigation is implemented in the All Data Grid. Grid Mode introduces inline cell editing and pending patch context tracking. A combined interstitial Data Quality Check for duplicate accounts and incomplete addresses fires automatically after workbook load. The `ADDRESS_INCOMPLETE_CANDIDATE` Matching System provides deterministic candidate matching for incomplete addresses, routing warnings and blockers to Pre-Flight.

## Modular Architecture
The architecture is modular, with components and engines extracted into namespaces:
- `window.AppModules.Components.*` extracted UI component modules
- `window.AppModules.Engines.*` extracted engine modules (from Phase B)
- `window.AppModules._registry` list of registered module paths
- `window.AppModules._version` current extraction version (C.1.0)

### Extracted Components (Phase C)
| Module | Source | Container ID |
|---|---|---|
| `Components.MetricStrip` | TriageAnalytics.renderHeader batch summary | `ta-batch-summary` |
| `Components.LifecycleRail` | TriageAnalytics._renderLifecycle | `ta-lifecycle-stages` |
| `Components.ContractSummaryTable` | TriageAnalytics._renderContractTable | `ta-contract-tbody` |
| `Components.PreflightIssueTable` | renderPreflightChecklist + renderPreflightResult | `preflight-checklist` |

### Shared Engines (Phase B)
| Module | Purpose |
|---|---|
| `Engines.ContextResolver` | Normalize patch context from raw selection |
| `Engines.PatchCompanion` | End-to-end patch lifecycle management |
| `Engines.TriageCache` | Lightweight triage analytics cache |
| `Engines.TriageTelemetry` | Pipeline telemetry reporting |
| `Engines.ContractIndexEngine` | Contract hierarchy indexing |
| `Engines.ContractHealthScore` | Health scoring engine |

### Grid Modules (Phase D1)
| Module | Source | Delegate Target |
|---|---|---|
| `Engines.GridState` | gridConfig + gridState objects | Column visibility, sort, filter, search, page state |
| `Components.GridHeader` | renderGridColumnHeaders | `all-data-thead` column header rendering + sort icons |
| `Components.GridTable` | renderGridBody + inline edit wiring | `all-data-tbody` row rendering, cell formatting, inline edit |

### Record Inspector Modules (Phase D2)
| Module | Source | Delegate Target |
|---|---|---|
| `Engines.RecordInspectorState` | srrState object | Record state, field states, filters, patch draft |
| `Components.RecordInspectorHeader` | Record Inspector header block | `srr-record-id`, `srr-state-badge`, `srr-title-record-name` identity, nav, file actions |
| `Components.RecordInspectorFieldList` | renderSrrFields + filters | `srr-field-list`, `srr-field-count` field rendering and filtering |
| `Components.RecordInspectorPatchRail` | patch panel expand/collapse/editor | Patch overlay open/close, editor render, patch list |

### PDF Viewer Modules (Phase D3)
| Module | Source | Delegate Target |
|---|---|---|
| `Engines.PdfViewerState` | srrState PDF fields + pdfMatchState | PDF URL, page, zoom, cache status, match state |
| `Components.PdfViewerToolbar` | page/zoom control functions | page/zoom controls and match bar |
| `Components.PdfViewerFrame` | srrLoadPdfForRecord/srrRenderPdf/srrShowEmptyState | frame rendering, load, error, anchor jump |

### Admin Panel Modules (Phase D4)
| Module | Source | Delegate Target |
|---|---|---|
| `Engines.AdminTabState` | currentAdminTab + alias map | Tab state, alias resolution, valid tab list |
| `Components.AdminTabsNav` | switchAdminTab panel/button logic | panel show/hide, button styling, architect rail |
| `Components.AdminTabGovernance` | governance tab activation | batch add toggles, batch merge refresh |
| `Components.AdminTabSchemaStandards` | standardizer tab activation | unknown columns table refresh |
| `Components.AdminTabPatchOps` | patch-ops tab activation | admin queue, patch console rendering |
| `Components.AdminTabPeopleAccess` | people tab activation | people sub-tab restore |
| `Components.AdminTabQARunner` | qa-runner tab activation | QARunner tab open handler |
| `Components.AdminTabRuntimeConfig` | runtime-config tab activation | glossary summary render |

### Audit Timeline Modules (Phase D5)
| Module | Source | Delegate Target |
|---|---|---|
| `Engines.AuditTimelineState` | AuditTimeline store + query/filter | memCache access, query, actor resolution, canonical event names |
| `Components.AuditTimelinePanel` | openFullAuditPanel/close/refresh/export | panel open/close, badge, dropdown, export |
| `Components.AuditTimelineFilters` | filter selects + quick chips + presets | filter get/set, quick chips, presets |

### DataSource/Import Modules (Phase D6)
| Module | Source | Delegate Target |
|---|---|---|
| `Engines.ImportState` | handleFileImport + import flags | Import state tracking, file type detection, parse status |
| `Engines.WorkbookSessionStore` | saveWorkbookToCache/loadWorkbookFromCache + session ops | Workbook cache save/load/clear, named session save/load/list |
| `Components.DataSourcePanel` | openDataSourcePanel/closeDataSourceDrawer | panel open/close, file input |

### System Pass Modules (Phase D7)
| Module | Source | Delegate Target |
|---|---|---|
| `Engines.SystemPassState` | SystemPass object | Proposals, run/rerun, accept/reject, bulk actions, hinge detection, sort/filter |
| `Components.SystemPassPanel` | rerunSystemPass/cancelSystemPassRerun/executeSystemPassRerun + renderSystemPassResults | panel open/close, rerun, render |
| `Components.SystemPassActions` | acceptSystemPassProposal/rejectSystemPassProposal + bulk accept/reject | Single and bulk proposal actions with delegate wiring |

### Patch Validation: Future-Only Fields
- `blacklist_category` and `rfi_target` are defined in the patch draft schema but are future-only features with no current required/optional enforcement. They appear as empty-string placeholders and must not be treated as active validation fields.

### Deterministic Logs
- `[APP-MODULES][P1C] registered:` module registration
- `[APP-MODULES][P1C] bootstrap_complete` Phase B engine registration
- `[APP-MODULES][P1D1] grid_modules_registered` Phase D1 grid module registration
- `[APP-MODULES][P1D2] inspector_modules_registered` Phase D2 all 4 inspector modules registered
- `[APP-MODULES][P1D3] pdf_viewer_modules_registered` Phase D3 all 3 PDF viewer modules registered
- `[APP-MODULES][P1D4] admin_modules_registered` Phase D4 all 8 admin modules registered
- `[APP-MODULES][P1D5] audit_timeline_modules_registered` Phase D5 all 3 audit timeline modules registered
- `[APP-MODULES][P1D6] datasource_modules_registered` Phase D6 all 3 datasource modules registered
- `[IMPORT-D6] source_opened/parse_started/parse_finished/session_saved/session_loaded` import flow observability
- `[APP-MODULES][P1D7] systempass_modules_registered` Phase D7 all 3 system pass modules registered
- `[SYSTEMPASS-D7] panel_opened` system pass reason picker opened
- `[SYSTEMPASS-D7] rerun_started/rerun_finished` system pass rerun lifecycle
- `[SYSTEMPASS-D7] proposal_action` single proposal accept/reject
- `[SYSTEMPASS-D7] bulk_action` bulk accept/reject action
- `[PATCH-COMP][P1B]` patch panel operations (open, submit, cancel, draft)

## External Dependencies
A FastAPI server acts as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF. SheetJS (XLSX) is loaded via CDN for Excel import/export functionality. The application integrates modules for:
- **Contract Composite Grid**: Enhances the All Data Grid with nested, collapsible contract sections.
- **Batch PDF Scan**: Adds batch-level PDF scanning for mojibake/non-searchable content.
- **Canonical Contract Triage View**: Adds canonical triage metrics and contract-centric terminology.
- **PDF Reliability Spike**: Diagnoses and hardens PDF anchor search reliability.
- **Contract Health Pre-Flight Table**: Replaces card-based grouping with a single unified nested table for contract health.
- **Real-Time Pre-Flight Intake**: Provides real-time visibility into batch PDF scanning.
- **Clean-to-SystemPass Routing**: Routes clean-scanned contracts to the System Pass queue.
- **Contract Health Score**: A lifecycle-wide health scoring engine tracking contract health with a 0-100 score.
- **Data Quality Check (Combined Interstitial)**: A unified modal for duplicate account detection and incomplete address candidate matching.
- **ADDRESS_INCOMPLETE_CANDIDATE Matching System**: Deterministic candidate matching for incomplete addresses.
