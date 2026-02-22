# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed to define, validate, and preview semantic rules offline. Its core purpose is to enhance semantic rule management, reduce errors, and boost decision-making efficiency by capturing semantic decisions as reviewable configuration artifacts and operating with deterministic outputs in an offline-first manner. The business vision is to deliver a robust platform for managing complex semantic rules, ensuring data integrity, and facilitating efficient operational decision-making.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system employs a Config Pack Model with strict version matching and a 12-status patch request lifecycle, including comment systems and role-based access control. The UI/UX features a dashboard with a queue-centric sidebar, right-side drawers, role-based navigation, and a Patch Studio for drafting, preflight checks, live previews, and revision tracking. Data handling supports CSV/XLSX import, inline editing, a lock-on-commit mechanism with a change map engine, and workbook session caching.

Semantic rules adhere to a WHEN/THEN pattern, generating deterministic cell-level signals for validation and grid coloring. Authentication employs Google OAuth for human users and scoped API keys for service ingestion, with strict workspace isolation. A sandbox/demo mode is available.

Key features include a "Contract Line Item Wizard," XLSX export, Audit Timeline, Schema Tree Editor, Batch Merge, `SystemPass` for deterministic changes, `UndoManager` for session-scoped draft edits, `RollbackEngine` for governed rollback artifacts, and a Triage Analytics module. An Evidence Viewer provides document-level text anchoring, a corrections workflow, RFI custody tracking, and an interactive panel with unified click behavior for validation. A heuristic suggestion engine analyzes source document column headers, proposing mappings to canonical glossary terms.

Document Mode Preflight provides deterministic page/document classification and quality gating for PDF documents. An Admin Sandbox Preflight Test Lab allows testing single PDFs and generating detailed reports. An OGC Preparation Simulator enables operators to run preflight, review results, and export deterministic `prep_export_v0` JSON.

Glossary Fuzzy Confidence Scoring uses a 6-component weighted formula for candidate scoring, categorizing confidence into HIGH, MEDIUM, LOW, and HIDDEN buckets, with deterministic tie-breaking. Normalization includes NFKC, lowercase, punctuation stripping, and noise token removal.

The PTL (Patch-to-Live) Pipeline provides a governed workflow for promoting analyst patch requests from sandbox to production. The V3 Unified Contract Workspace — Record Inspector V2 Beta, merges the Contract Generator, Preflight Test Lab, and Record Inspector into a single integrated view, supporting an end-to-end flow: upload PDF → preflight gate → resolution story → contract generation → patch submission.

The system uses Python 3.11 with FastAPI and Uvicorn for the backend, and PostgreSQL 16 as the database. The frontend is built with vanilla JavaScript, using `ui/viewer/theme.css` for styling and supporting light/dark modes.

## External Dependencies
- **FastAPI server**: Used as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF.
- **SheetJS (XLSX)**: Integrated for Excel import/export functionality.
- **Google Drive**: Integrated as a data source for contract workbook import/export, with role-based folder routing for XLSX exports.
- **Google OAuth**: Used for user authentication.
- **PostgreSQL**: Hosted on Supabase for the primary database.