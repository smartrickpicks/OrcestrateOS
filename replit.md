# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed for defining, validating, and previewing semantic rules offline. It serves as a single source of semantic truth, aiming to streamline patch requests, improve operator ergonomics, and provide an analyst-first reference for explicit, deterministic, and auditable decisions. The system captures semantic decisions as reviewable configuration artifacts, operates offline-first, and ensures deterministic outputs using only the Python standard library for local previews. Its business vision is to improve semantic rule management, reduce errors, and enhance decision-making efficiency.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system captures semantic decisions as reviewable configuration artifacts and employs a canonical join strategy for data handling. It utilizes a Config Pack Model with strict version matching, supporting a 12-status lifecycle for patch requests (10 visible + 2 hidden), including comment systems and role-based access control (Analyst, Verifier, Admin, Architect).

The UI features a dashboard with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are organized into six tabs. A Patch Studio facilitates drafting, preflight checks, and evidence packing with live previews and revision tracking. UI elements include color-coded grid highlighting, Excel-style column headers, and a PDF viewer.

Data handling supports CSV/XLSX import, inline editing, and a lock-on-commit mechanism with a change map engine tracking cell-level changes. Workbook session caching persists uploaded Excel data to IndexedDB. Triage Analytics uses normalized key comparison and `COLUMN_ALIAS_MAP` for schema matching.

Semantic rules generate deterministic cell-level signals on dataset load using `field_meta.json` and `qa_flags.json` for validation, populating Analyst Triage queues and driving grid coloring. Rules follow a WHEN/THEN pattern. Record identity is defined by `tenant_id`, `division_id`, `dataset_id`, `record_id`. The system uses email-based access control with Google sign-in for production OAuth.

Features include a "Contract Line Item Wizard" for batch adding and deduplication and export functionality for XLSX files including data, change logs, signals summaries, and metadata. An Audit Timeline system uses an IndexedDB-backed store for all governance actions.

A Schema Tree Editor manages the canonical rules bundle, including `field_meta.json`, `hinge_groups.json`, `sheet_order.json`, `qa_flags.json`, `document_types.json`, and `column_aliases.json`. A Batch Merge feature allows combining source batches into a single governance container, with explicit rule promotion for tenant rules.

A `SystemPass` module provides a deterministic, rerunnable, proposal-only engine for system changes. Pre-Flight triage buckets handle blockers like unknown columns or unreadable OCR. A Contract Index Engine builds a hierarchy of batch, contract, document, contract section, row.

`UndoManager` provides local, session-scoped undo for draft-only inline edits. `RollbackEngine` creates governed rollback artifacts at four scopes (field, patch, contract, batch), capturing before/after state snapshots.

The Triage Analytics module aggregates metrics. Record Inspector Guidance provides section-specific advice. Sandbox mode is permissionless; Production uses strict role gates. A TruthPack module with an `architect` role enables a clean-room state machine for calibration and baseline marking. A Role Registry with stable role IDs, permission-based access checks, and a People workspace are integrated.

The system routes to triage by default for all roles. Contract-first navigation is implemented in the All Data Grid. Grid Mode introduces inline cell editing and pending patch context tracking. A combined interstitial Data Quality Check for duplicate accounts and incomplete addresses fires automatically after workbook load. The `ADDRESS_INCOMPLETE_CANDIDATE` Matching System provides deterministic candidate matching for incomplete addresses, routing warnings and blockers to Pre-Flight.

The architecture is modular, with components and engines extracted into namespaces like `window.AppModules.Components.*` and `window.AppModules.Engines.*`. The extraction is through Phase D15 (Rollback/Undo) with 55 total modules (51 explicit + 4 dynamic Phase C).

## API v2.5 Initiative (Gate 5 COMPLETE + Google OAuth)
The system is undergoing a multi-gate upgrade to add Postgres-backed multi-user persistence:
- **Gate 1 (Docs):** COMPLETE — Readiness report, DB decision lock, canonical API spec, OpenAPI 3.1, AsyncAPI 2.6, dependency-aware task list
- **Gate 2 (Clarity):** COMPLETE — Q1 locked (Google OAuth + scoped API keys), Q2 locked (single DB with workspace_id scoping), 11 decisions frozen
- **Gate 3 (Alignment):** COMPLETE — Final task plan frozen (30 tasks, 4 phases), contract lock summary, alignment packet
- **Gate 4 (Code):** COMPLETE — Phase 1 (Persistence Foundation) + Phase 2 (All 15 resources)
- **Gate 5 (Audit):** COMPLETE — 36/36 smoke tests passing, all 9 non-negotiables met
- **Key docs:** `docs/api/API_SPEC_V2_5_CANONICAL.md`, `docs/api/openapi.yaml`, `docs/api/asyncapi.yaml`, `docs/decisions/DECISION_V25_DB.md`, `docs/handoff/V25_READINESS_REPORT.md`, `docs/handoff/V25_TASK_LIST.md`, `docs/handoff/V25_CLARITY_MATRIX.md`, `docs/handoff/V25_LOCKED_DECISIONS.md`, `docs/handoff/V25_FINAL_TASK_PLAN.md`, `docs/handoff/V25_CONTRACT_LOCK.md`, `docs/handoff/V25_GATE3_ALIGNMENT_PACKET.md`, `docs/handoff/V25_GATE4_LOCK_CHECKS.md`, `docs/handoff/V25_GATE5_COMPLIANCE_PACKET.md`
- **Non-negotiables:** Resource-based routes, PATCH for transitions, ULID primaries, optimistic concurrency (409 STALE_VERSION), no-self-approval server-enforced, append-only audit_events, Postgres canonical
- **Auth policy:** Google OAuth (OIDC) for human users, scoped API keys for service ingestion, dual-accept on reads
- **Workspace isolation:** Single DB, strict workspace_id FK scoping, composite indexes, optional RLS
- **Server modules:** `server/db.py` (connection pool), `server/migrate.py` (migration runner), `server/ulid.py` (ID generator), `server/api_v25.py` (API router + health endpoint), `server/auth.py` (RBAC + auth resolution + JWT decode + inactive user denial), `server/audit.py` (audit event emission), `server/jwt_utils.py` (HS256 JWT sign/verify)
- **Route modules:** `server/routes/workspaces.py` (Workspace CRUD), `server/routes/batches.py` (Batch CRUD), `server/routes/patches.py` (Patch CRUD + 22-transition matrix + self-approval gate), `server/routes/auth_google.py` (Google OAuth verify + config + /me), `server/routes/members.py` (Member CRUD, admin-only)
- **Phase 2 COMPLETE:** All 15 resources implemented — Workspace, Batch, Patch, Contract, Document, Account, Annotation, EvidencePack, RFI, TriageItem, Signal, SelectionCapture, AuditEvent (read-only), SSE stream, Health
- **Google OAuth COMPLETE:** Full login flow — Google Sign-In → backend ID token verification → email-based user matching → active status check → workspace role resolution → JWT issuance → frontend Bearer auth
- **JWT session layer:** HS256 signing with 24-hour expiry, inactive user DB check on every JWT auth request
- **Members CRUD:** Admin-only member management persists to Postgres via API (GET/POST/PATCH/DELETE)
- **RFI DB persistence:** Frontend RFI submissions POST to `/api/v2.5/workspaces/{ws_id}/rfis` with JWT auth, persisting to Postgres `rfis` table with audit trail. RFIs bypass preflight gates but require justification (evidence gate).
- **Auth smoke tests:** 10/10 PASS — config, JWT auth, inactive user JWT denial, unlisted user denial, role scoping, member management, secret safety, validation
- **Seeded users:** 9 Create Music Group employees + 4 demo users in workspace `ws_SEED0100000000000000000000`
- **Migration 003:** `server/migrations/003_auth_google_oauth.sql` — adds `status` and `google_sub` columns to users table, seeds CMG users

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