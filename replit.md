# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed for defining, validating, and previewing semantic rules offline. It serves as a single source of semantic truth to streamline patch requests, improve operator ergonomics, and provide an analyst-first reference for explicit, deterministic, and auditable decisions. The system aims to improve semantic rule management, reduce errors, and enhance decision-making efficiency by capturing semantic decisions as reviewable configuration artifacts and operating offline-first with deterministic outputs.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system employs a Config Pack Model with strict version matching, supporting a 12-status lifecycle for patch requests, including comment systems and role-based access control (Analyst, Verifier, Admin, Architect). UI/UX features include a dashboard with a queue-centric sidebar, right-side drawers, role-based navigation, and a Patch Studio for drafting and preflight checks with live previews and revision tracking. Data handling supports CSV/XLSX import, inline editing, a lock-on-commit mechanism with a change map engine, and workbook session caching to IndexedDB.

Semantic rules, defined by a WHEN/THEN pattern, generate deterministic cell-level signals using `field_meta.json` and `qa_flags.json` for validation, populating Analyst Triage queues and driving grid coloring. Access control is email-based with Google sign-in. Key features include a "Contract Line Item Wizard," XLSX export capabilities, and an Audit Timeline system. A Schema Tree Editor manages the canonical rules bundle, and a Batch Merge feature allows combining source batches. The `SystemPass` module provides a deterministic, rerunnable engine for system changes, and `UndoManager` offers session-scoped undo for draft edits. `RollbackEngine` creates governed rollback artifacts at various scopes. The Triage Analytics module aggregates metrics, and a Role Registry manages user permissions. The system includes contract-first navigation, a combined interstitial Data Quality Check, and an `ADDRESS_INCOMPLETE_CANDIDATE` Matching System. The architecture is modular, with components extracted into distinct namespaces.

The system is undergoing an upgrade to add Postgres-backed multi-user persistence, featuring resource-based routes, ULID primaries, optimistic concurrency, and server-enforced no-self-approval. Authentication uses Google OAuth for human users and scoped API keys for service ingestion, with strict workspace isolation.

An Evidence Inspector is being added for document-level text anchoring, corrections, and RFI custody tracking, utilizing new database tables for anchors, corrections, and OCR escalations, and introducing a feature flag for controlled rollout.

## External Dependencies
- **FastAPI server**: Used as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF.
- **SheetJS (XLSX)**: Integrated via CDN for Excel import/export functionality.
- **Google Drive**: Being integrated as a data source for contract workbook import/export.