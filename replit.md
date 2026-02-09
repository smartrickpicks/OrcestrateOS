# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed to define, validate, and preview semantic rules offline. It acts as a single source of semantic truth, enabling rule authoring and review as configuration. The project aims to improve operator ergonomics, streamline the patch request and review pipeline, and provide an analyst-first reference with clear interfaces for explicit, deterministic, and auditable decisions. It captures semantic decisions as reviewable configuration artifacts and operates offline-first, ensuring deterministic outputs using only the Python standard library for local previews.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The core design involves capturing semantic decisions as reviewable configuration artifacts. Data handling employs a canonical join strategy and a Config Pack Model with strict version matching. The system supports an 11-status lifecycle for patch requests, including comment systems and role-based access control (Analyst, Verifier, Admin, Architect).

The UI features a dashboard with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are presented in a workflow-ordered view. A Patch Studio enables drafting, preflight checks, and evidence packing with live previews and revision tracking. UI elements include color-coded grid highlighting, Excel-style column headers, and a PDF viewer. Record Inspection (SRR) provides navigation.

Data handling supports CSV/XLSX import, a Field Inspector for search-filtered fields, inline editing, and a lock-on-commit mechanism. A change map engine tracks cell-level changes. The Verifier Triage uses a 4-queue system, and a localStorage-backed mock filesystem manages artifacts. Workbook session caching persists uploaded Excel data to IndexedDB, supporting multi-session storage and auto-save.

Semantic rules generate deterministic cell-level signals on dataset load using `field_meta.json` and `qa_flags.json` for validation, populating Analyst Triage queues and driving grid coloring. Rules follow a WHEN/THEN pattern. Record identity is defined by `tenant_id`, `division_id`, `dataset_id`, `record_id`. The system uses email-based access control with Google sign-in for production OAuth.

Features include "Catalog Items Group" for batch adding and deduplication, and a `_document_type` and `_capabilities` object per record, with document types loaded from `config/document_types.json`. Export functionality generates XLSX files including all data sheets, change logs, signals summaries, and metadata. An Audit Timeline system uses an IndexedDB-backed store for all governance actions, accessible via a UI with filtering options and exportable to XLSX.

The system incorporates a Schema Tree Editor for managing the canonical rules bundle, including `field_meta.json`, `hinge_groups.json`, `sheet_order.json`, `qa_flags.json`, `document_types.json`, and `column_aliases.json`. It supports column alias resolution and tracking of schema changes. A Batch Merge feature allows combining source batches into a single governance container, with explicit rule promotion for tenant rules.

Document roles are inferred with user confirmation. A `SystemPass` module provides a deterministic, rerunnable, proposal-only engine for system changes, routed to a "System Changes" triage bucket. Pre-Flight triage buckets handle blockers like unknown columns or unreadable OCR. A Contract Index Engine builds a hierarchy of batch→contract→document→sheet→row, persisting summary references to SessionDB.

The `SystemPass.acceptProposal()` for hinge-field proposals auto-creates a `system_suggested` patch artifact and routes it through the standard patch lifecycle. `UndoManager` provides local, session-scoped undo for draft-only SRR inline edits. `RollbackEngine` creates governed rollback artifacts at 4 scopes (field, patch, contract, batch), capturing before/after state snapshots and triggering reruns if hinge-field modifications are detected. Audit events are generated for all these actions.

The Triage Analytics module aggregates metrics from various stores into a lightweight cache, rendering above the triage grid with 3-lane cards (Pre-Flight, Semantic, Patch Review), a horizontal lifecycle tracker, and a contract summary drilldown table. Triage Telemetry provides live pipeline telemetry with processing status banners, lifecycle deltas, and derived contract state chips. Record Inspector Guidance provides section-specific advice and knowledge links.

Contract ID derivation enforces priority (extracted path ID → hash(canonical URL) → fallback signature). ContractIndex is always rebuilt from the workbook on all load paths. Unknown column routing uses sheet-scoped frequency voting for contract attachment with severity thresholds. Header-echo rows are removed at parse time. Sandbox mode is permissionless; Production uses strict role gates. A Pre-Flight Calibration Suite ensures the accuracy of pre-flight detectors. A TruthPack module with an `architect` role enables a clean-room state machine for calibration and baseline marking.

## External Dependencies
A FastAPI server acts as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF. SheetJS (XLSX) is loaded via CDN for Excel import/export functionality.