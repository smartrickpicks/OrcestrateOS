# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed for defining, validating, and previewing semantic rules offline. It serves as a single source of semantic truth to streamline patch requests, improve operator ergonomics, and provide an analyst-first reference for explicit, deterministic, and auditable decisions. The system aims to improve semantic rule management, reduce errors, and enhance decision-making efficiency by capturing semantic decisions as reviewable configuration artifacts and operating offline-first with deterministic outputs.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system employs a Config Pack Model with strict version matching, supporting a 12-status lifecycle for patch requests, including comment systems and role-based access control (Analyst, Verifier, Admin, Architect). UI/UX features include a dashboard with a queue-centric sidebar, right-side drawers, role-based navigation, and a Patch Studio for drafting and preflight checks with live previews and revision tracking. Data handling supports CSV/XLSX import, inline editing, a lock-on-commit mechanism with a change map engine, and workbook session caching to IndexedDB.

Semantic rules, defined by a WHEN/THEN pattern, generate deterministic cell-level signals using `field_meta.json` and `qa_flags.json` for validation, populating Analyst Triage queues and driving grid coloring. Access control is email-based with Google sign-in. Key features include a "Contract Line Item Wizard," XLSX export capabilities, and an Audit Timeline system. A Schema Tree Editor manages the canonical rules bundle, and a Batch Merge feature allows combining source batches. The `SystemPass` module provides a deterministic, rerunnable engine for system changes, and `UndoManager` offers session-scoped undo for draft edits. `RollbackEngine` creates governed rollback artifacts at various scopes. The Triage Analytics module aggregates metrics, and a Role Registry manages user permissions. The system includes contract-first navigation, a combined interstitial Data Quality Check, and an `ADDRESS_INCOMPLETE_CANDIDATE` Matching System. The architecture is modular, with components extracted into distinct namespaces.

The system is undergoing an upgrade to add Postgres-backed multi-user persistence, featuring resource-based routes, ULID primaries, optimistic concurrency, and server-enforced no-self-approval. Authentication uses Google OAuth for human users and scoped API keys for service ingestion, with strict workspace isolation.

An Evidence Viewer (v2.51) is fully implemented with document-level text anchoring, corrections workflow, and RFI custody tracking. All phases complete:
- Phase 1-3: Foundation, Reader+Anchors, RFI Custody+Corrections (backend + DB)
- Phase 4: Hardening (role enforcement, OCR idempotency, Mojibake Gate UI)
- Phase 5: Finalization (Reader/PDF toggle, anchor scroll mapping, 37-test suite)
- Phase 6 (UI): Evidence Viewer interactive panel in the right sidebar with three collapsible sections:
  - **Anchors Panel**: Create anchors from text selection in Reader view, list with click-to-scroll, delete capability (soft-delete via DELETE /anchors/{id})
  - **Corrections Panel**: View corrections with status chips (auto_applied/pending_verifier/approved/rejected), Approve/Reject buttons role-gated to verifier/admin/architect
  - **RFI Custody Panel**: View RFIs filtered to current document context, custody state badges (open/awaiting_verifier/returned_to_analyst/resolved/dismissed), role-appropriate action buttons (analyst: Send; verifier: Return/Resolve/Dismiss)
  - Feature-flag gated: tab only appears when EVIDENCE_INSPECTOR_V251=true (checked via GET /api/v2.5/feature-flags endpoint)
  - JS functions prefixed `ei*`, CSS classes prefixed `.ei-`, state in `_eiState` global
All behind `EVIDENCE_INSPECTOR_V251` feature flag. 37/37 smoke tests pass.

## Mode Unification (Evidence Viewer Mode)
The "Grid" mode has been renamed to "Evidence Viewer" mode with unified click behavior:
- **Review mode**: Unchanged — click a row to open Record Inspector in full review layout.
- **Evidence Viewer mode**: First single-click on any cell opens the Evidence Viewer panel for that record (no validation). Subsequent single-clicks on the same record validate cells (toggle green). Clicking a different record switches context. Double-click opens context menu.
- **Context menu**: Includes "Open in Review Mode" action that switches to Review mode and navigates to the current record.
- **State machine**: `_evState` object tracks `mode` (review/evidence_viewer), `viewerOpen`, `activeRecordId`, `activeSheetName`, `activeRowIdx`, `clickArmedAfterOpen`.
- Transitions: T1 (mode toggle), T2 (first click opens viewer), T3 (subsequent clicks validate), T4 (double-click context menu), T5 (Open in Review Mode), T6 (toggle back to review preserves record).

## External Dependencies
- **FastAPI server**: Used as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF.
- **SheetJS (XLSX)**: Integrated via CDN for Excel import/export functionality.
- **Google Drive**: Being integrated as a data source for contract workbook import/export.