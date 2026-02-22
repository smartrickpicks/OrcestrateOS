# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed to define, validate, and preview semantic rules offline. Its core purpose is to enhance semantic rule management, reduce errors, and boost decision-making efficiency by capturing semantic decisions as reviewable configuration artifacts and operating with deterministic outputs in an offline-first manner. The business vision is to deliver a robust platform for managing complex semantic rules, ensuring data integrity, and facilitating efficient operational decision-making.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system employs a Config Pack Model with strict version matching and a 12-status patch request lifecycle, including comment systems and role-based access control. The UI/UX features a dashboard with a queue-centric sidebar, right-side drawers, role-based navigation, and a Patch Studio for drafting, preflight checks, live previews, and revision tracking. Data handling supports CSV/XLSX import, inline editing, a lock-on-commit mechanism with a change map engine, and workbook session caching. The Admin Panel is organized into Pipeline, Schema & Standards, Quality & Gates, Patch Ops, and People & Access sections.

Semantic rules adhere to a WHEN/THEN pattern, generating deterministic cell-level signals for validation and grid coloring. Authentication employs Google OAuth for human users and scoped API keys for service ingestion, with strict workspace isolation. A sandbox/demo mode is available. Key features include a "Contract Line Item Wizard," XLSX export, Audit Timeline, Schema Tree Editor, Batch Merge, `SystemPass` for deterministic changes, `UndoManager` for session-scoped draft edits, `RollbackEngine` for governed rollback artifacts, and a Triage Analytics module. An Evidence Viewer provides document-level text anchoring, a corrections workflow, RFI custody tracking, and an interactive panel with unified click behavior for validation. Reader mode includes text extraction, formatting, Mojibake inline detection, and OCR escalation.

A heuristic suggestion engine analyzes source document column headers, proposing mappings to canonical glossary terms using various matching techniques. The UI Suggestions Panel features keyword overlay highlighting, linked fields, and a compact diagnostics status line. Document Mode Preflight provides deterministic page/document classification and quality gating for PDF documents. An Admin Sandbox Preflight Test Lab allows testing single PDFs and generating detailed reports. An OGC Preparation Simulator enables operators to run preflight, review results, and export deterministic `prep_export_v0` JSON.

Glossary Fuzzy Confidence Scoring uses a 6-component weighted formula for candidate scoring, categorizing confidence into HIGH, MEDIUM, LOW, and HIDDEN buckets, with deterministic tie-breaking. Normalization includes NFKC, lowercase, punctuation stripping, and noise token removal. Export Contract Hardening validates cached state completeness before building export payloads.

The OGC Preparation Simulator Operations View provides a multi-batch, DB-first governance queue, unifying patches, RFIs, and corrections into a single feed. The Verifier Organizational View provides a workspace-level governance dashboard with KPI summaries and batch management, guarded by RBAC, which is unified into a canonical `#page-triage` frame for a role-adaptive interface.

The UI supports Dark Mode v2 ("Subtle Futuristic Neon Control Panel") using `ui/viewer/theme.css` as the single source of truth for all color tokens, supporting both light and dark modes with persistent toggles. The Sidebar Icon System uses inline SVG icons with `currentColor` inheritance, and the Collapsible Sidebar feature persists state to localStorage.

Google Drive Save (XLSX Export) supports hierarchical folder routing with per-member priority and automatic folder bootstrapping. The workbook structure includes DATA sheets, GOV_META, ACTIONS, STATE_JSON, and legacy sheets.

Field Suggestions UI upgrade adds collapsible section headers with per-section status pills, localStorage-based collapse persistence, right-click context menu for field cards, and dark mode CSS variable fixes. The CSV-backed Account Resolver provides 3-tier deterministic matching (exact → token overlap → edit distance) against `CMG_Account.csv` via `AccountIndex`. Preflight Test Lab — Salesforce Match Integration wires the Salesforce account resolver into the preflight pipeline. The UI renders a matrix-style table with Source Text, Mapped Account, Match Status, Confidence, and Evidence columns.

Multi-Account Aware Composite Scoring adds context-aware scoring via `server/resolvers/context_scorer.py`. Each candidate gets a composite score based on name, address, account context, and service penalty. The UI renders visible and hidden rows with chip color coding and a Debug toggle. Resolution Story adds `build_resolution_story()` to `server/preflight_engine.py`, producing a structured narrative from SF match results. CMG-side gating ensures `legal_entity_account` must be a CMG entity. New Entry Detection identifies and flags counterparties not found in the Salesforce account index, generating an `onboarding_recommendation`. Party extraction uses `_extract_recital_parties()` with preamble-only parsing.

Deterministic Contract Classification uses `server/data/preflight_contract_rules.v1.json` as the single source of truth for contract categories, expected schedule types, and termination flavors. `server/preflight_rules.py` evaluates the rules JSON deterministically.

The Patch Submit Modal replaces the old Patch tab in the SRR sidebar with a centered modal dialog, requiring justification for corrections. Reconstruction Completion Gates integrate a multi-step progression (`generateCopyDone`, `reconstructionCompleteDone`, `overrideRedDone`) into the Contract Generator, enforcing specific actions based on gate status (GREEN, YELLOW, RED).

The Resolver Data Feed (`server/routes/resolver_feed.py`) exposes canonical Salesforce resolver datasets to the CGB frontend via `/api/v2.5/resolver/accounts` (paginated, searchable) and `/api/v2.5/resolver/accounts/summary`).

The Patch-to-Live (PTL) Pipeline provides a governed workflow for promoting analyst patch requests from sandbox to production, with `srrCheckSyncPreflightGate()` enforcing gate progression. The PTL footer is simplified, and patch-submit buttons are moved into the workspace modal flow.

The Analyst Sandbox Triage Queue (Queue 0) is gated by `RECORD_INSPECTOR_V2` and provides localStorage-backed CRUD for sandbox preflight triage items. Single PDF uploads and batch preflight via imported spreadsheets queue items for async processing, with progress UI and deep-linking to preflight results.

The V3 Unified Contract Workspace — Record Inspector V2 Beta merges the Contract Generator, Preflight Test Lab, and Record Inspector into a single integrated view, supporting an end-to-end flow from PDF upload to patch submission through seven phases, with 15 audit event types emitted.

## External Dependencies
- **Backend:** Python 3.11, FastAPI + Uvicorn, PyMuPDF, openpyxl, playwright, psycopg2-binary, google-auth, rapidfuzz, sse-starlette, pytest
- **Database:** PostgreSQL 16 (Supabase-hosted)
- **Frontend:** Vanilla JavaScript (no framework, no build step)
- **Node.js:** Node 22 (for `@redocly/cli` and verification scripts only)
- **Integrations:** SheetJS (XLSX), Google Drive (workbook import/export), Google OAuth