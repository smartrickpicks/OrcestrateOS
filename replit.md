# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed to define, validate, and preview semantic rules offline. It acts as a single source of semantic truth for authoring and reviewing semantic rules as configuration. The project aims to enhance operator ergonomics, streamline the patch request and review pipeline, and provide an analyst-first reference for explicit, deterministic, and auditable decisions. It captures semantic decisions as reviewable configuration artifacts and operates offline-first, ensuring deterministic outputs using only the Python standard library for local previews.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The core design principle involves capturing semantic decisions as reviewable configuration artifacts. The system employs a canonical join strategy for data handling and a Config Pack Model with strict version matching. It supports an 11-status lifecycle for patch requests, including comment systems and role-based access control (Analyst, Verifier, Admin, Architect).

The UI features a dashboard with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are presented in a workflow-ordered view. A Patch Studio facilitates drafting, preflight checks, and evidence packing with live previews and revision tracking. UI elements include color-coded grid highlighting, Excel-style column headers, and a PDF viewer.

Data handling supports CSV/XLSX import, inline editing, and a lock-on-commit mechanism. A change map engine tracks cell-level changes. The Verifier Triage uses a 4-queue system, and a localStorage-backed mock filesystem manages artifacts. Workbook session caching persists uploaded Excel data to IndexedDB, supporting multi-session storage and auto-save. Triage Analytics schema matching uses normalized key comparison and `COLUMN_ALIAS_MAP` resolution.

Semantic rules generate deterministic cell-level signals on dataset load using `field_meta.json` and `qa_flags.json` for validation, populating Analyst Triage queues and driving grid coloring. Rules follow a WHEN/THEN pattern. Record identity is defined by `tenant_id`, `division_id`, `dataset_id`, `record_id`. The system uses email-based access control with Google sign-in for production OAuth.

Features include a "Catalog Item Wizard" for batch adding and deduplication with metadata-driven validation. Export functionality generates XLSX files including all data, change logs, signals summaries, and metadata. An Audit Timeline system uses an IndexedDB-backed store for all governance actions, accessible via a UI with filtering and export options.

The system incorporates a Schema Tree Editor for managing the canonical rules bundle, including `field_meta.json`, `hinge_groups.json`, `sheet_order.json`, `qa_flags.json`, `document_types.json`, and `column_aliases.json`. It supports column alias resolution and tracking of schema changes. A Batch Merge feature allows combining source batches into a single governance container, with explicit rule promotion for tenant rules.

Document roles are inferred with user confirmation. A `SystemPass` module provides a deterministic, rerunnable, proposal-only engine for system changes, routed to a "System Changes" triage bucket. Pre-Flight triage buckets handle blockers like unknown columns or unreadable OCR. A Contract Index Engine builds a hierarchy of batch→contract→document→sheet→row, persisting summary references to SessionDB.

`UndoManager` provides local, session-scoped undo for draft-only inline edits. `RollbackEngine` creates governed rollback artifacts at 4 scopes (field, patch, contract, batch), capturing before/after state snapshots. Audit events are generated for all these actions.

The Triage Analytics module aggregates metrics into a lightweight cache. Triage Telemetry provides live pipeline telemetry with processing status banners and lifecycle deltas. Record Inspector Guidance provides section-specific advice.

Contract ID derivation enforces priority. ContractIndex is always rebuilt from the workbook on all load paths. Unknown column routing uses sheet-scoped frequency voting for contract attachment. Header-echo rows are removed at parse time. Sandbox mode is permissionless; Production uses strict role gates. A Pre-Flight Calibration Suite ensures the accuracy of pre-flight detectors. A TruthPack module with an `architect` role enables a clean-room state machine for calibration and baseline marking. A Role Registry with stable role IDs, permission-based access checks, and a People workspace are integrated. Truth Config versioning stores baselines in SessionDB with a test_mode/established lifecycle and rollback capability. An Invite system provides single-use invite creation, use, and revocation with audit events.

The system routes to triage by default for all roles. Contract-first navigation is implemented in the All Data Grid. A legacy double-slash annotation sanitizer cleans URL and business fields during XLSX and CSV parsing. Pre-Flight items now include sheet-specific tabs and human-readable labels for blockers.

## External Dependencies
A FastAPI server acts as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF. SheetJS (XLSX) is loaded via CDN for Excel import/export functionality. The application includes several modules for specific functionalities:
- **P1C Contract Composite Grid**: Enhances the All Data Grid with nested, collapsible sheet sections when a specific contract is selected.
- **P1F Batch PDF Scan**: Adds batch-level PDF scanning for mojibake/non-searchable content on workbook load, routing flagged contracts to Pre-Flight.
- **P1X Canonical Contract Triage View**: Adds canonical triage metrics and contract-centric terminology, refining how sheets count towards canonical record totals and displaying OCR issues.
- **P1E PDF Reliability Spike**: Diagnoses and hardens PDF anchor search reliability, including mojibake/non-searchable detection and improved anchor matching strategies.
- **P1D.1 Contract Health Pre-Flight Table**: Replaces card-based grouping with a single unified nested table for contract health, displaying parent contract rows with expandable child issue rows.
- **P1F.1 Real-Time Pre-Flight Intake**: Provides real-time visibility into the batch PDF scan as it processes files, displaying live status and immediately emitting Pre-Flight items upon detection.
- **P1F.2 Clean-to-SystemPass Routing**: Routes clean-scanned contracts to the System Pass queue as `PDF_VERIFIED_CLEAN` signals. Adds contract rollup status fields.
- **P1G Contract Health Score**: A lifecycle-wide health scoring engine that tracks contract health from extraction through promotion. Computes a 0-100 score using a penalty model. Health bands are Critical (0-34), At Risk (35-59), Watch (60-84), Healthy (85-100). Health column appears in Contract Summary table plus all lifecycle queue tables, with colored band chips and penalty breakdown tooltips. Filter chips allow filtering Contract Summary by health band. Worst-first sorting surfaces critical contracts. Trend tracking shows score deltas between refreshes.