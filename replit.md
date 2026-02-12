# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed for defining, validating, and previewing semantic rules offline. It serves as a single source of semantic truth, aiming to streamline patch requests, improve operator ergonomics, and provide an analyst-first reference for explicit, deterministic, and auditable decisions. The system captures semantic decisions as reviewable configuration artifacts, operates offline-first, and ensures deterministic outputs using only the Python standard library for local previews. Its business vision is to improve semantic rule management, reduce errors, and enhance decision-making efficiency.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system captures semantic decisions as reviewable configuration artifacts and employs a canonical join strategy for data handling. It utilizes a Config Pack Model with strict version matching, supporting an 11-status lifecycle for patch requests, including comment systems and role-based access control (Analyst, Verifier, Admin, Architect).

The UI features a dashboard with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are organized into six tabs. A Patch Studio facilitates drafting, preflight checks, and evidence packing with live previews and revision tracking. UI elements include color-coded grid highlighting, Excel-style column headers, and a PDF viewer.

Data handling supports CSV/XLSX import, inline editing, and a lock-on-commit mechanism with a change map engine tracking cell-level changes. Workbook session caching persists uploaded Excel data to IndexedDB. Triage Analytics uses normalized key comparison and `COLUMN_ALIAS_MAP` for schema matching.

Semantic rules generate deterministic cell-level signals on dataset load using `field_meta.json` and `qa_flags.json` for validation, populating Analyst Triage queues and driving grid coloring. Rules follow a WHEN/THEN pattern. Record identity is defined by `tenant_id`, `division_id`, `dataset_id`, `record_id`. The system uses email-based access control with Google sign-in for production OAuth.

Features include a "Contract Line Item Wizard" for batch adding and deduplication and export functionality for XLSX files including data, change logs, signals summaries, and metadata. An Audit Timeline system uses an IndexedDB-backed store for all governance actions.

A Schema Tree Editor manages the canonical rules bundle, including `field_meta.json`, `hinge_groups.json`, `sheet_order.json`, `qa_flags.json`, `document_types.json`, and `column_aliases.json`. A Batch Merge feature allows combining source batches into a single governance container, with explicit rule promotion for tenant rules.

A `SystemPass` module provides a deterministic, rerunnable, proposal-only engine for system changes. Pre-Flight triage buckets handle blockers like unknown columns or unreadable OCR. A Contract Index Engine builds a hierarchy of batch, contract, document, contract section, row.

`UndoManager` provides local, session-scoped undo for draft-only inline edits. `RollbackEngine` creates governed rollback artifacts at four scopes (field, patch, contract, batch), capturing before/after state snapshots.

The Triage Analytics module aggregates metrics. Record Inspector Guidance provides section-specific advice. Sandbox mode is permissionless; Production uses strict role gates. A TruthPack module with an `architect` role enables a clean-room state machine for calibration and baseline marking. A Role Registry with stable role IDs, permission-based access checks, and a People workspace are integrated.

The system routes to triage by default for all roles. Contract-first navigation is implemented in the All Data Grid. Grid Mode introduces inline cell editing and pending patch context tracking. A combined interstitial Data Quality Check for duplicate accounts and incomplete addresses fires automatically after workbook load. The `ADDRESS_INCOMPLETE_CANDIDATE` Matching System provides deterministic candidate matching for incomplete addresses, routing warnings and blockers to Pre-Flight.

The architecture is modular, with components and engines extracted into namespaces like `window.AppModules.Components.*` and `window.AppModules.Engines.*`. The extraction is through Phase D13 (Contract Index) with 50 total modules (46 explicit + 4 dynamic Phase C).

## External Dependencies
- **FastAPI server**: Acts as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF.
- **SheetJS (XLSX)**: Loaded via CDN for Excel import/export functionality.
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