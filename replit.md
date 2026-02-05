# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane. Its primary purpose is to define, validate, and preview semantic rules offline, serving as a single source of semantic truth. It enables rule authoring and review as configuration, providing an analyst-first reference with clear interfaces and checklists for explicit, deterministic, and auditable decisions. The project aims to improve operator ergonomics and streamline the patch request and review pipeline.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Decisions
Orchestrate OS functions as a governance-only control plane, capturing semantic decisions as reviewable configuration artifacts without runtime execution, APIs, credentials, or prompts. It emphasizes offline-first determinism, ensuring identical outputs for the same inputs through local previews using only the Python standard library. The system employs a canonical join strategy (`contract_key` → `file_url` → `file_name`) and a Config Pack Model (`config_pack.base.json` for baseline, `config_pack.patch.json` for changes) with strict version matching.

### UI/UX and Workflow
The user interface features a dashboard shell with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are presented in a workflow-ordered view with Plain-English, Payload, and Master tabs, supported by extensive tooltips and Plain English explanations. The system implements an 11-status lifecycle for patch requests, including comment systems, role-based access control (Analyst, Verifier, Admin), and a Patch Studio for drafting, preflight checks, and evidence packing with live previews and revision tracking. UI/UX decisions include enforcing hard page separation, RBAC route guards, and explicit page labels. Grid cells display color-coded highlighting based on change type (corrections, RFIs, system changes, blacklist) with a color legend for the modified dataset. The All Data Grid features Excel-style column headers (A, B, C...), drag-and-drop column reordering, and preferred column ordering (File_Name_c and Account_Name_c first); File_Name fields are clickable hyperlinks to file_url with hidden URL column. The PDF viewer is configured for single-column continuous scroll with hidden thumbnail sidebar.

### Data Handling and Integration
Data loading in demo mode defaults to `ostereo_demo_v1.json` (the modified export with meta sheets) on cold start; production mode loads with no sample data and shows "No dataset loaded" until a data source is connected. An "Upload Excel" button in the sticky header provides a failsafe import method for .xlsx/.xls files (not CSV). The system supports CSV/XLSX import with delimiter inference and utilities for resetting demo state. A PDF proxy (FastAPI server on port 5000) handles CORS-safe PDF fetching and field resolution using `<object>` elements for display. A Field Inspector provides search-filtered fields, inline editing, and a lock-on-commit mechanism, highlighting fields with signals and displaying patch details. Glossary hover tooltips (v1.6.36) appear on the ⓘ icon next to each field label, showing metadata from field_meta.json (field label, type, required/optional status, definition, options) and hinge group from hinge_groups.json; fields without metadata display "No glossary data available." A change map engine parses meta sheets (`_change_log` and `RFIs & Analyst Notes`) to build cell-level change tracking for the modified dataset. Meta sheet propagation ensures `RFIs & Analyst Notes` entries are seeded into canonical stores: RFIs (Note_Type = "RFI") go to PATCH_REQUEST_STORE for cross-role visibility, Manual Review items (Note_Type = "Manual Review") go to META_TRIAGE_STORE for Analyst triage, and *_change_log sheets populate the System Changes queue with address standardizations and rule corrections. Datasets missing meta sheets are handled gracefully with warning logs. The Verifier Triage uses a 4-queue system, and a localStorage-backed mock filesystem manages artifacts with a deterministic artifact ID system. A Canonical Record Store persists records to localStorage, enabling Single Row Review (SRR) rehydration. Picklist/options fields are supported, rendering as dropdowns in the Field Inspector with validation for invalid values.

### Semantic Rules and Signals
The system generates deterministic cell-level signals on dataset load using `field_meta.json` and `qa_flags.json` for validation (e.g., `MISSING_REQUIRED`, `PICKLIST_INVALID`, `MOJIBAKE_DETECTED`, `QA_FLAG`). These signals populate Analyst Triage queues and drive grid coloring and row badges. Field Inspector ordering is derived from `field_meta.json`, `hinge_groups.json`, and `sheet_order.json` from the `/rules/rules_bundle/`. Rules follow a WHEN/THEN pattern with `rule_id`, conditions, and actions.

### Identity and Authentication
Record identity is defined by `tenant_id`, `division_id`, `dataset_id`, `record_id`, with `record_id` generated based on a canonicalized row fingerprint. A production-style landing page with Google sign-in handles user authentication, supporting `?role=admin|reviewer` URL parameters for testing. Admin-only Playground mode allows role switching, while Analyst/Reviewer users are locked to their roles. User creation and management are available in the Admin Panel for Demo/Playground mode, with changes persisting to localStorage. Production Google OAuth login checks a configured user list for role assignment.

### Export / Save Functionality
The Export/Save button generates an XLSX file using SheetJS with all data sheets, changelog, RFI notes, and signals summary. The export includes:
- All data sheets with original structure preserved
- `_change_log` sheet with corrections, status changes, and audit trail
- `RFIs & Analyst Notes` sheet with all analyst questions and responses
- `_signals_summary` sheet with validation flags and semantic signals
- `_orchestrate_meta` sheet with dataset metadata, version info, and nomenclature

Exported files are named `orchestrate_{dataset_id}_{timestamp}.xlsx` and downloaded directly to the user's device.

## External Dependencies
None by design. This repository exclusively uses the Python standard library, with no external Python packages, database connections, API integrations, runtime services, or credentials/secrets. A FastAPI server is used as a local PDF proxy for CORS-safe PDF fetching. SheetJS (XLSX) is loaded via CDN for Excel import/export functionality.