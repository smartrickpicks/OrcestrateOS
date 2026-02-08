# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed to define, validate, and preview semantic rules offline. It acts as a single source of semantic truth, enabling rule authoring and review as configuration. The project aims to improve operator ergonomics, streamline the patch request and review pipeline, and provide an analyst-first reference with clear interfaces for explicit, deterministic, and auditable decisions.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Decisions
Orchestrate OS is a governance-only control plane that captures semantic decisions as reviewable configuration artifacts. It operates offline-first, ensuring deterministic outputs using only the Python standard library for local previews. Key data handling includes a canonical join strategy (`contract_key` → `file_url` → `file_name`) and a Config Pack Model (`config_pack.base.json` for baseline, `config_pack.patch.json` for changes) with strict version matching.

### UI/UX and Workflow
The user interface features a dashboard with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are presented in a workflow-ordered view with Plain-English, Payload, and Master tabs. The system supports an 11-status lifecycle for patch requests, including comment systems, role-based access control (Analyst, Verifier, Admin), and a Patch Studio for drafting, preflight checks, and evidence packing with live previews and revision tracking. UI elements include color-coded grid highlighting for change types, Excel-style column headers with drag-and-drop reordering, and a PDF viewer configured for single-column continuous scroll. Record Inspection (SRR) provides Previous/Next navigation, a position indicator, and auto-advances to the next record upon completion. A file action bar allows editing and downloading files.

### Data Handling and Integration
The system supports CSV/XLSX import with delimiter inference and provides a failsafe "Upload Excel" button. It features a Field Inspector for search-filtered fields, inline editing, and a lock-on-commit mechanism. Glossary hover tooltips provide field metadata. A change map engine tracks cell-level changes from meta sheets (`_change_log`, `RFIs & Analyst Notes`), propagating entries to canonical stores (`PATCH_REQUEST_STORE`, `META_TRIAGE_STORE`, `System Changes queue`). The Verifier Triage uses a 4-queue system, and a localStorage-backed mock filesystem manages artifacts. A Canonical Record Store persists records to localStorage for Single Row Review rehydration. Picklist/options fields are supported with validation. Review Checklist gating enforces role-specific approval checklists. Workbook session caching persists uploaded Excel data to IndexedDB, with multi-session storage for up to 10 named sessions and an auto-save feature.

### Semantic Rules and Signals
The system generates deterministic cell-level signals on dataset load using `field_meta.json` and `qa_flags.json` for validation (e.g., `MISSING_REQUIRED`, `PICKLIST_INVALID`, `MOJIBAKE_DETECTED`, `QA_FLAG`). These signals populate Analyst Triage queues and drive grid coloring. Field Inspector ordering is derived from `field_meta.json`, `hinge_groups.json`, and `sheet_order.json` from the `/rules/rules_bundle/`. Rules follow a WHEN/THEN pattern.

### Identity and Authentication
Record identity is defined by `tenant_id`, `division_id`, `dataset_id`, `record_id`. The landing page uses email-based access control validated against an Admin Panel user list, assigning roles accordingly. Returning users are greeted with a "Welcome back" card. Google sign-in is available for production OAuth. Session persistence automatically redirects authenticated users to their last page. Patch submission enforces gate parity, requires a Replay Contract for Correction and Blacklist patches, and prevents self-approval.

### Catalog Items Grouping + Safe Batch Add
This feature allows analysts to group records under a "Catalog Items Group" and batch-add missing items with safe deduplication. Any record can be marked as a Group Anchor, and child rows inherit `group_id`. Safe deduplication normalizes text and compares items using bigram similarity, categorizing them as Existing, Possible Duplicate, or New. A 3-step wizard (Paste List → Preview → Confirm) facilitates the process.

### Document Type + Capabilities Model
Each record carries a `_document_type` and `_capabilities` object. Document types are loaded from `config/document_types.json`. Catalog Items functionality sets `capabilities.catalog_items = true`. Export includes `document_type`, `capabilities`, and `group_id` as flat columns. Grid nesting visually indents child rows under anchor rows.

### Export / Save Functionality
The Export/Save button generates an XLSX file using SheetJS, including all data sheets, `_change_log`, `RFIs & Analyst Notes`, `_signals_summary`, and `_orchestrate_meta` (dataset metadata). Exported files are named `orchestrate_{dataset_id}_{timestamp}.xlsx`.

### Session Isolation + Role Audit (v1.6.58)
Fixed session bleed between users: signing in as a different user (or role) now clears stale localStorage keys (ingestion_folder_name, nav state, viewer mode, SRR state, group state, workbook sessions, artifact playground). Sign-out also clears these keys. Demo page normalized: "Reviewer" role renamed to "Verifier" across demoProfiles, data-role attributes, and button labels to match viewer's internal setMode. Playground mode restricted: in demo mode, only Admin gets the role switcher; Analyst and Verifier are locked to their assigned roles (matching production behavior). Legacy normalizeLegacyRole() and normalizeLegacyStatus() preserved for backward compatibility.

### Audit Log (v1.6.59)
The Audit Timeline system uses an IndexedDB-backed store (`orchestrate_audit`) with a memory cache hydrated from IndexedDB on init for synchronous XLSX export after page reloads. All governance actions (patch submit, field verify/blacklist/correct, verifier approve/reject, admin promote, batch add, catalog group set, session restore) emit persisted timeline events with actor, role, timestamp, and record context. The Audit Log UI reads from this store with filters for event type, actor role, and patch request ID. The `Audit_Log` sheet is included in XLSX exports. No synthetic/demo events are generated at render time.

### V1 Polish (v1.6.60)
Status color consistency: `STATUS_COLOR_MAP` provides a single source of truth for status colors (ready, needs_review, blocked, finalized, flagged) used across grid rows, triage queue chips, and record inspection badges. A status color legend is displayed in the grid view. PDF anchor navigation no longer causes blank flash (removed intermediate `about:blank` reset). Grid row clicks always open Record Inspection; file downloads require explicit action only. Docs updated: Blacklist Category and RFI Target marked as V2-only/non-enforced in V1. Evidence Pack spec (`docs/ui/views/ui_evidence_pack.md`) created.

## External Dependencies
None by design. This repository uses only the Python standard library. A FastAPI server acts as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF. SheetJS (XLSX) is loaded via CDN for Excel import/export functionality.