# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed for defining, validating, and previewing semantic rules offline. It acts as a single source of semantic truth to streamline patch requests, enhance operator ergonomics, and provide an analyst-first reference for explicit, deterministic, and auditable decisions. The system aims to improve semantic rule management, reduce errors, and enhance decision-making efficiency by capturing semantic decisions as reviewable configuration artifacts and operating offline-first with deterministic outputs.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system utilizes a Config Pack Model with strict version matching and supports a 12-status lifecycle for patch requests, including comment systems and role-based access control. The UI/UX features a dashboard with a queue-centric sidebar, right-side drawers, role-based navigation, and a Patch Studio for drafting and preflight checks with live previews and revision tracking. Data handling supports CSV/XLSX import, inline editing, a lock-on-commit mechanism with a change map engine, and workbook session caching.

Admin Panel has 5 tabs: **Pipeline** (artifact registry, workflow map, demo dataset, contract line item wizard, merge batches), **Schema & Standards** (schema tree editor, unknown columns, canonical glossary), **Quality & Gates** (version & baseline, evidence gates, preflight test lab, QA runner, JSON inspector), **Patch Ops** (patch queue, patch requests console), **People & Access** (environment mode, members/roles/invites). The Architect Controls bar at the bottom is collapsible and remembers its state. Old tab names (qa-runner, runtime-config, config, inspector) are aliased to their new locations via `switchAdminTab()`.

Semantic rules follow a WHEN/THEN pattern, generating deterministic cell-level signals using metadata for validation, populating Analyst Triage queues, and driving grid coloring. Access control is email-based with Google sign-in. Key features include a "Contract Line Item Wizard," XLSX export capabilities, an Audit Timeline, a Schema Tree Editor for canonical rules bundles, and a Batch Merge feature. The architecture includes `SystemPass` for deterministic changes, `UndoManager` for session-scoped draft edits, `RollbackEngine` for governed rollback artifacts, and a Triage Analytics module.

The system supports Postgres-backed multi-user persistence with resource-based routes, ULID primaries, optimistic concurrency, and server-enforced no-self-approval. Authentication uses Google OAuth for human users and scoped API keys for service ingestion, with strict workspace isolation. Sandbox/demo mode uses a dev-only auth bypass (`_SANDBOX_AUTH_ALLOWED` in `server/auth.py`) that creates a synthetic admin auth when `X-Sandbox-Mode: true` header is present and no real auth resolves; this bypass is disabled in production deployments.

An Evidence Viewer provides document-level text anchoring, corrections workflow, and RFI custody tracking. It features an interactive panel with Anchors, Corrections, and RFI Custody sections. It supports unified click behavior for opening the panel and subsequent cell validation, and a context menu for "Review Mode." The Evidence Viewer mode uses a two-column layout with a document viewer (Reader/PDF toggle) and Evidence Details panel on the left, and the grid table on the right. Reader mode includes text extraction, formatting, Mojibake inline detection with visual classifications, and an OCR escalation CTA. A selection action menu allows creating Evidence Marks, RFIs, and Corrections, with policy-driven status assignments and RFI lifecycle propagation.

Grid Record Labels are standardized as `Contract: Account` or `Contract: Account: Opportunity` in the first, sticky data column.

Sandbox Session Management ensures sandbox-created artifacts persist indefinitely until explicitly reset by an admin, with options to "Reset Sandbox" or "Reset All Data."

A heuristic suggestion engine (v2) analyzes source document column headers and proposes mappings to canonical glossary terms using exact, fuzzy, and keyword matching strategies. Keyword scoring uses `field_meta.json` tokens (labels, definitions, picklist options) instead of hardcoded category buckets. A local-fallback mode (`/api/v2.5/suggestion-runs/local`) accepts source_fields directly from workbook headers without requiring a materialized document row. Diagnostics metadata (run_mode, field_meta availability, match distribution) is persisted in suggestion_runs.metadata and suggestions.metadata JSONB columns. The UI Suggestions Panel includes keyword overlay highlighting in the Evidence Viewer reader (Show/Clear per suggestion row), suggestion-derived Linked Fields with orange border when no real anchors exist, and a compact diagnostics status line showing run mode and match counts. Users can accept or decline suggestions, which auto-creates glossary aliases. This feature integrates with database tables for glossary terms, aliases, suggestion runs, and suggestions, and requires explicit workspace selection for glossary endpoints.

Section Metadata Integration groups and orders fields in the record inspector based on `enrichments.section_metadata`, falling back to legacy grouping if absent. Section Focus Guidance provides "what to look for" guidance based on `section_focus` from `enrichments.section_metadata` or `config/section_guidance.json`.

Module Registry manages system modules, including `Engines.SuggestionsState` and `Components.SuggestionsPanel`.

UX Fine-Tuning includes locked clarity decisions, slim section group headers, canonical field labels, sticky guidance cards, live contract chip refresh, bulk verification by section, inline mojibake character highlighting, and enhanced context menus. The "Create Alias" feature in the Evidence Viewer Reader allows creating glossary aliases directly from selected text, auto-populating grid cells, and creating evidence marks.

Enhanced Contract Line Items allow the batch add modal to capture source row context, enabling "duplicate row, change one field" workflows for adding missing records.

Document Mode Preflight provides a deterministic page/document classification and quality gate system for PDF documents, classifying pages as SEARCHABLE, SCANNED, or MIXED, and assigning gate colors (GREEN, YELLOW, RED) based on quality checks. It includes an Admin Sandbox Preflight Test Lab for running preflight on single PDFs, providing detailed reports.

## External Dependencies
- **FastAPI server**: Used as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF.
- **SheetJS (XLSX)**: Integrated for Excel import/export functionality.
- **Google Drive**: Integrated as a data source for contract workbook import/export.