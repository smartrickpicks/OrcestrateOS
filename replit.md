# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed to define, validate, and preview semantic rules offline. It acts as a single source of semantic truth, aiming to streamline patch requests, improve operator efficiency, and provide an analyst-centric reference for explicit, deterministic, and auditable decisions. The system's core purpose is to enhance semantic rule management, reduce errors, and boost decision-making efficiency by capturing semantic decisions as reviewable configuration artifacts and operating with deterministic outputs in an offline-first manner. Its business vision is to deliver a robust platform for managing complex semantic rules, ensuring data integrity, and facilitating efficient operational decision-making.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system utilizes a Config Pack Model with strict version matching and a 12-status lifecycle for patch requests, including comment systems and role-based access control. The UI/UX features a dashboard with a queue-centric sidebar, right-side drawers, role-based navigation, and a Patch Studio for drafting and preflight checks with live previews and revision tracking. Data handling supports CSV/XLSX import, inline editing, a lock-on-commit mechanism with a change map engine, and workbook session caching.

The Admin Panel is organized into five tabs: Pipeline, Schema & Standards, Quality & Gates, Patch Ops, and People & Access. Semantic rules follow a WHEN/THEN pattern, generating deterministic cell-level signals for validation and grid coloring. Authentication uses Google OAuth for human users and scoped API keys for service ingestion, with strict workspace isolation. A sandbox/demo mode is available.

Key features include a "Contract Line Item Wizard," XLSX export, Audit Timeline, Schema Tree Editor, Batch Merge, `SystemPass` for deterministic changes, `UndoManager` for session-scoped draft edits, `RollbackEngine` for governed rollback artifacts, and a Triage Analytics module.

An Evidence Viewer provides document-level text anchoring, a corrections workflow, RFI custody tracking, and an interactive panel with unified click behavior for validation. It supports a two-column layout with a document viewer (Reader/PDF toggle) and an Evidence Details panel. Reader mode includes text extraction, formatting, Mojibake inline detection, and OCR escalation. A selection action menu allows creating Evidence Marks, RFIs, and Corrections. Sandbox Session Management ensures artifact persistence.

A heuristic suggestion engine analyzes source document column headers, proposing mappings to canonical glossary terms using exact, fuzzy, and keyword matching. It includes a local-fallback mode and persists diagnostics metadata. The UI Suggestions Panel features keyword overlay highlighting, linked fields, and a compact diagnostics status line. Users can accept/decline suggestions, which auto-creates glossary aliases. Section Metadata Integration groups and orders fields in the record inspector, providing "what to look for" guidance. A Module Registry manages system modules.

UX Fine-Tuning includes locked clarity decisions, slim section group headers, canonical field labels, sticky guidance cards, live contract chip refresh, bulk verification by section, inline mojibake character highlighting, and enhanced context menus. The "Create Alias" feature allows creating glossary aliases directly from selected text. Enhanced Contract Line Items support batch add workflows.

Document Mode Preflight provides deterministic page/document classification and quality gating for PDF documents. An Admin Sandbox Preflight Test Lab allows testing single PDFs and generating detailed reports. An OGC Preparation Simulator (v0), an admin-only sandbox feature, enables operators to run preflight, review results in a gate-driven modal, toggle OGC Preview, and export deterministic `prep_export_v0` JSON.

Glossary Fuzzy Confidence Scoring uses a 6-component weighted formula for candidate scoring, categorizing confidence into HIGH, MEDIUM, LOW, and HIDDEN buckets, with deterministic tie-breaking. Normalization includes NFKC, lowercase, punctuation stripping, and noise token removal. Candidate suppression filters out irrelevant strings. Entity-specific handling preserves numeric-leading names. The UI shows top candidates with confidence percentages and reason chips.

Body Text Candidate Extraction identifies domain-relevant phrases from PDF body text, merging them with header candidates and scoring them together. Single-Token Domain Boost applies a specific boost for single-token candidates matching multi-token glossary entries. Category Starvation Prevention (`_apply_category_balance()`) ensures balanced representation across glossary categories. Scoring Config Freeze centralizes all scoring weights, thresholds, and boost multipliers. Export Contract Hardening validates cached state completeness before building export payloads.

A Salesforce Resolver Stub (`server/resolvers/salesforce.py`) provides an interface contract for entity resolution.

The OGC Preparation Simulator Operations View provides a multi-batch, DB-first governance queue, unifying patches, RFIs, and corrections into a single feed. Feature flags enable gradual migration to a PostgreSQL-backed Annotation Layer.

The Verifier Organizational View provides a workspace-level governance dashboard with KPI summaries, batch queues, batch drill-downs, and a filter bar, guarded by RBAC. Verifier Triage Unification migrates this view into a canonical `#page-triage` frame, creating a role-adaptive interface.

Dark Mode v2 ("Subtle Futuristic Neon Control Panel") uses `ui/viewer/theme.css` as the single source of truth for all color tokens, supporting both light and dark modes. The toggle persists to localStorage. The Sidebar Icon System uses inline SVG icons with `currentColor` inheritance. A Collapsible Sidebar feature persists state to localStorage.

Google Drive Save (XLSX Export) supports hierarchical folder routing with per-member priority and automatic folder bootstrapping. The export filename format is `{batch_id}-{actor}-{status}-{timestamp}.xlsx`. The workbook structure includes DATA sheets, GOV_META, ACTIONS, STATE_JSON, and legacy sheets. Workspace drive folder settings are configurable via the Admin panel.

Field Suggestions UI upgrade adds collapsible section headers with per-section status pills, localStorage-based collapse persistence, right-click context menu for field cards, and dark mode CSS variable fixes. The CSV-backed Account Resolver provides 3-tier deterministic matching (exact → token overlap → edit distance) against `CMG_Account.csv` via `AccountIndex`.

Preflight Test Lab — Salesforce Match Integration wires the Salesforce account resolver into the preflight pipeline. The preflight engine uses `extract_account_candidates` with strict extraction logic and header fallback. The UI renders a matrix-style table with Source Text, Mapped Account, Match Status, Confidence, and Evidence columns, positioned after encoding findings.

Multi-Account Aware Composite Scoring adds context-aware scoring via `server/resolvers/context_scorer.py`. Each candidate gets a composite score based on name, address, account context, and service penalty. Multiple valid accounts are retained if they have sufficient evidence. Account-context boosts use two-tier cues (strong/weak). Proximity uses strict and soft windows. Service-context penalty is source-aware. Address evidence is candidate-local. Scoring tiers are defined for full/partial address verification. Match status mapping defines 'match', 'review', and 'no-match' based on composite score. The UI renders visible and hidden rows with chip color coding and a Debug toggle.

Candidate extraction uses a hard denylist to suppress legal/common noise tokens unless extracted via strict label:value. Single-token uppercase words (≤6 chars) are also denied. Ranking sorts by source_type priority, then status, then confidence, then source alpha.

Resolution Story P0 adds `build_resolution_story()` to `server/preflight_engine.py`, producing a structured narrative from SF match results. CMG-side gating is a locked rule: `legal_entity_account` must be a CMG entity. If no CMG candidate passes threshold, `legal_entity_account = null` and `requires_manual_confirmation = true`. `counterparties[]` contains non-CMG candidates above a review threshold. Role selection is confidence-first within role constraints. `_guess_agreement_type()` uses a keyword-weighted heuristic.

New Entry Detection (v2.57+): When CMG legal entity is resolved but a counterparty extracted from the contract party/recital block is not found in the Salesforce account index, the system sets `new_entry_detected=true`, populates `unresolved_counterparties[]`, and generates an `onboarding_recommendation` with suggested account name, type (Record Label/Company/Artist heuristic), and reason. The frontend shows a prominent "NEW ENTRY DETECTED" banner and a read-only onboarding recommendation card. Party extraction uses `_extract_recital_parties()` with BETWEEN/PARTIES zone regex, filtering noise tokens. `_build_onboarding_recommendation()` uses company markers + agreement type for account type inference.

Patch Submit Modal (v2.57+) replaces the old Patch tab in the SRR sidebar with a centered modal dialog. The SRR left panel now has only two tabs: Edit and Info (Patch tab removed). After any action (field edit + Submit, RFI chip, Blacklist chip), a modal opens showing: patch type badge, context-appropriate summary (changes for corrections, field info for RFIs, subject for blacklists), evidence fields for corrections (Observation WHEN, Expected THEN, Repro Method dropdowns), and a required justification textarea. The modal uses `_patchModalOpen`, `_patchModalClose`, `_patchModalConfirmSubmit`, and `_srrExecutePatchSubmit` functions. CSS uses `.patch-submit-modal-*` classes with dark mode support. `_srrExpandPatchPanel`, `_srrCollapsePatchPanel`, `_srrTogglePatchPanel` are now no-ops. `srrBlacklistField` and `srrRfiField` auto-open the modal. `srrOnPatchTypeChange` opens the modal for RFI/Blacklist actions. A case-sensitivity fix in `canTransition()` normalizes role names to match `STATUS_TRANSITIONS` role arrays.

## External Dependencies
- **FastAPI server**: Used as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF.
- **SheetJS (XLSX)**: Integrated for Excel import/export functionality.
- **Google Drive**: Integrated as a data source for contract workbook import/export, with role-based folder routing for XLSX exports.