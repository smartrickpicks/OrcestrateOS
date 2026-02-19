# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed for defining, validating, and previewing semantic rules offline. It acts as a single source of semantic truth to streamline patch requests, enhance operator ergonomics, and provide an analyst-first reference for explicit, deterministic, and auditable decisions. The system aims to improve semantic rule management, reduce errors, and enhance decision-making efficiency by capturing semantic decisions as reviewable configuration artifacts and operating offline-first with deterministic outputs. Its business vision is to provide a robust platform for managing complex semantic rules, ensuring data integrity, and facilitating efficient decision-making in various operational contexts.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system utilizes a Config Pack Model with strict version matching and supports a 12-status lifecycle for patch requests, including comment systems and role-based access control. The UI/UX features a dashboard with a queue-centric sidebar, right-side drawers, role-based navigation, and a Patch Studio for drafting and preflight checks with live previews and revision tracking. Data handling supports CSV/XLSX import, inline editing, a lock-on-commit mechanism with a change map engine, and workbook session caching.

The Admin Panel is structured into five key tabs: Pipeline, Schema & Standards, Quality & Gates, Patch Ops, and People & Access. Semantic rules follow a WHEN/THEN pattern, generating deterministic cell-level signals for validation and grid coloring. Access control is email-based via Google sign-in. Key features include a "Contract Line Item Wizard," XLSX export, an Audit Timeline, a Schema Tree Editor, and a Batch Merge feature. The architecture includes `SystemPass` for deterministic changes, `UndoManager` for session-scoped draft edits, `RollbackEngine` for governed rollback artifacts, and a Triage Analytics module.

The system supports Postgres-backed multi-user persistence with resource-based routes, ULID primaries, optimistic concurrency, and server-enforced no-self-approval. Authentication uses Google OAuth for human users and scoped API keys for service ingestion, with strict workspace isolation. A sandbox/demo mode is available for development.

An Evidence Viewer provides document-level text anchoring, a corrections workflow, and RFI custody tracking, featuring an interactive panel and unified click behavior for validation. It supports a two-column layout with a document viewer (Reader/PDF toggle) and an Evidence Details panel, with Reader mode supporting text extraction, formatting, Mojibake inline detection, and OCR escalation. Document Text Search is available in both the Evidence Viewer and Review/SRR panel, supporting both Reader and PDF modes.

A heuristic suggestion engine (v2) analyzes source document column headers, proposing mappings to canonical glossary terms using exact, fuzzy, and keyword matching. The UI Suggestions Panel features keyword overlay highlighting, linked fields, and a compact diagnostics status line. Section Metadata Integration groups and orders fields in the record inspector.

UX Fine-Tuning includes locked clarity decisions, slim section group headers, canonical field labels, sticky guidance cards, live contract chip refresh, bulk verification by section, inline mojibake character highlighting, and enhanced context menus. The "Create Alias" feature in the Evidence Viewer Reader allows creating glossary aliases directly from selected text. Enhanced Contract Line Items support batch add workflows.

Document Mode Preflight provides deterministic page/document classification and quality gating for PDF documents. An OGC Preparation Simulator enables operators to run preflight and review results.

Glossary Fuzzy Confidence Scoring uses a 6-component weighted formula for candidate scoring, categorizing confidence into HIGH, MEDIUM, LOW, and HIDDEN buckets with deterministic tie-breaking rules. Normalization includes NFKC, lowercase, punctuation stripping, and noise token removal. Body Text Candidate Extraction identifies domain-relevant phrases from PDF body text using sliding word windows and filters.

The OGC Preparation Simulator Operations View provides a multi-batch, DB-first governance queue for verifiers/admins, unifying patches, RFIs, and corrections into a single feed. The Verifier Organizational View (`#/verifier-org`) provides a workspace-level governance dashboard. Verifier Triage Unification migrates this functionality into the canonical `#page-triage` frame, creating a role-adaptive interface.

Dark Mode v2 ("Subtle Futuristic Neon Control Panel") uses `ui/viewer/theme.css` as the single source of truth for all color tokens, defining a consistent color palette across the application.

The Sidebar Icon System uses inline SVG icons with `currentColor` inheritance. A Collapsible Sidebar feature allows users to collapse the navigation for more screen real estate.

Google Drive Save (XLSX Export) supports hierarchical folder routing with per-member priority and automatic folder bootstrap. The workbook structure includes DATA sheets, GOV_META, ACTIONS, and STATE_JSON.

Analyst Pending Patch Visualization displays the analyst's proposed value in grid cells that have pending RFI or correction patches.

Patch Submission Modal provides a centralized modal dialog for submitting patch requests (corrections and RFIs) directly from the record inspector.

Salesforce Multi-Account Matching uses `server/resolvers/account_index.py`, `server/resolvers/context_scorer.py`, and enhanced `server/resolvers/salesforce.py`. The preflight engine (`server/preflight_engine.py`) includes `_run_salesforce_match()`, `build_resolution_story()`, and `build_opportunity_spine()` for deterministic contract spine completeness checks.

## External Dependencies
- **FastAPI server**: Used as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF.
- **SheetJS (XLSX)**: Integrated for Excel import/export functionality.
- **Google Drive**: Integrated as a data source for contract workbook import/export, with role-based folder routing for XLSX exports.