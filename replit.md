# Orchestrate OS — Semantic Control Board

## Overview

Orchestrate OS is a governance-only semantic control plane for DataDash + Kiwi, designed to define, validate, and preview semantic rules offline. Its core purpose is to serve as a single source of semantic truth, enabling rule authoring and review as configuration rather than code. It aims to provide an analyst-first reference with clear interfaces and checklists, ensuring explicit, deterministic, and auditable decisions. The project focuses on improving operator ergonomics and streamlining the patch request and review pipeline, ultimately providing a single source of semantic truth for improved data governance.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Core Design Decisions

Orchestrate OS functions as a governance-only control plane, capturing all semantic decisions as reviewable configuration artifacts without runtime execution, APIs, credentials, or prompts. It emphasizes offline-first determinism, ensuring identical outputs for the same inputs through local previews using only the Python standard library. The system employs a canonical join strategy (`contract_key` → `file_url` → `file_name`) and a Config Pack Model (`config_pack.base.json` for baseline, `config_pack.patch.json` for changes) with strict version matching.

### UI/UX and Workflow

The user interface features a dashboard shell with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are presented in a workflow-ordered view with Plain-English, Payload, and Master tabs, supported by extensive tooltips and Plain English explanations. The system implements a robust 11-status lifecycle for patch requests, including comment systems, role-based access control (Analyst, Verifier, Admin), and a Patch Studio for drafting, preflight checks, and evidence packing with live previews and revision tracking. UI/UX decisions include enforcing hard page separation, RBAC route guards, and explicit page labels.

### Data Handling and Integration

Data loading defaults to `ostereo_demo_original.json` on cold start (v1.6.4). On fresh page load without a saved session, the app automatically fetches and loads the baseline demo dataset from `/examples/datasets/ostereo_demo_original.json`. Admin users can toggle between "Original" (baseline) and "Modified" (in-progress) datasets via the demo toggle in Admin settings. The toggle state persists in localStorage. Meta sheets (change logs, RFIs, etc.) are hidden from navigation but available as audit log data via the Audit Log button in SRR. The Data Source drawer includes a "Demo Dataset" section with a clickable card to load the demo data manually. Supports CSV/XLSX import with delimiter inference, and utilities for resetting demo state. The system includes a PDF proxy (FastAPI server on port 5000) for CORS-safe PDF fetching and field resolution, and utilizes `<object>` elements for PDF display. A Field Inspector and Patch Editor provide search-filtered fields, inline editing, and a lock-on-commit mechanism. v1.6.5 hides internal fields from the Inspector (File_URL_c, metrics fields) while displaying the file name in the panel header; hidden fields remain accessible internally for PDF loading. The system features a Verifier Triage with a 4-queue system and automatic view swapping based on roles, plus a localStorage-backed mock filesystem for artifacts and a deterministic artifact ID system. A Canonical Record Store persists records to localStorage, enabling Single Row Review (SRR) rehydration.

### Semantic Rules and Signals

The system generates deterministic cell-level signals on dataset load using `field_meta.json` and `qa_flags.json` for validation (e.g., `MISSING_REQUIRED`, `PICKLIST_INVALID`, `MOJIBAKE_DETECTED`, `QA_FLAG`). These signals populate Analyst Triage queues, and drive grid coloring and row badges in the All-Data Grid, with cell coloring based on signal priority. Field Inspector ordering is derived from `field_meta.json`, `hinge_groups.json`, and `sheet_order.json` from the `/rules/rules_bundle/`. Rules follow a WHEN/THEN pattern with `rule_id`, conditions (sheet, field, operator, value), and actions (action, sheet, field, severity).

### Identity and Authentication

Record identity is defined by `tenant_id`, `division_id`, `dataset_id`, `record_id`, with `record_id` generated based on a canonicalized row fingerprint. A landing page with mock Google sign-in and role selection (Analyst/Reviewer/Admin) handles user authentication and role-based access. Folder-based data sources are auto-mapped from user email.

## External Dependencies

None by design. This repository exclusively uses the Python standard library. It has no external Python packages, database connections, API integrations, runtime services, or credentials/secrets.