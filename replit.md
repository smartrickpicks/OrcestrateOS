# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed to define, validate, and preview semantic rules offline. It acts as a single source of semantic truth to streamline patch requests, improve operator efficiency, and provide an analyst-centric reference for explicit, deterministic, and auditable decisions. Its core purpose is to enhance semantic rule management, reduce errors, and boost decision-making efficiency by capturing semantic decisions as reviewable configuration artifacts and operating with deterministic outputs in an offline-first manner. The business vision is to deliver a robust platform for managing complex semantic rules, ensuring data integrity, and facilitating efficient operational decision-making.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The system employs a Config Pack Model with strict version matching and a 12-status patch request lifecycle, including comment systems and role-based access control. The UI/UX features a dashboard with a queue-centric sidebar, right-side drawers, role-based navigation, and a Patch Studio for drafting, preflight checks, live previews, and revision tracking. Data handling supports CSV/XLSX import, inline editing, a lock-on-commit mechanism with a change map engine, and workbook session caching.

The Admin Panel is organized into Pipeline, Schema & Standards, Quality & Gates, Patch Ops, and People & Access sections. Semantic rules adhere to a WHEN/THEN pattern, generating deterministic cell-level signals for validation and grid coloring. Authentication employs Google OAuth for human users and scoped API keys for service ingestion, with strict workspace isolation. A sandbox/demo mode is available.

Key features include a "Contract Line Item Wizard," XLSX export, Audit Timeline, Schema Tree Editor, Batch Merge, `SystemPass` for deterministic changes, `UndoManager` for session-scoped draft edits, `RollbackEngine` for governed rollback artifacts, and a Triage Analytics module. An Evidence Viewer provides document-level text anchoring, a corrections workflow, RFI custody tracking, and an interactive panel with unified click behavior for validation. Reader mode includes text extraction, formatting, Mojibake inline detection, and OCR escalation. Sandbox Session Management ensures artifact persistence.

A heuristic suggestion engine analyzes source document column headers, proposing mappings to canonical glossary terms using various matching techniques. The UI Suggestions Panel features keyword overlay highlighting, linked fields, and a compact diagnostics status line. Users can accept/decline suggestions, which auto-creates glossary aliases. Section Metadata Integration groups and orders fields in the record inspector.

UX Fine-Tuning includes locked clarity decisions, slim section group headers, canonical field labels, sticky guidance cards, live contract chip refresh, bulk verification by section, inline mojibake character highlighting, and enhanced context menus. The "Create Alias" feature allows creating glossary aliases directly from selected text. Enhanced Contract Line Items support batch add workflows.

Document Mode Preflight provides deterministic page/document classification and quality gating for PDF documents. An Admin Sandbox Preflight Test Lab allows testing single PDFs and generating detailed reports. An OGC Preparation Simulator (v0), an admin-only sandbox feature, enables operators to run preflight, review results in a gate-driven modal, toggle OGC Preview, and export deterministic `prep_export_v0` JSON.

Glossary Fuzzy Confidence Scoring uses a 6-component weighted formula for candidate scoring, categorizing confidence into HIGH, MEDIUM, LOW, and HIDDEN buckets, with deterministic tie-breaking. Normalization includes NFKC, lowercase, punctuation stripping, and noise token removal. Candidate suppression filters out irrelevant strings. Single-Token Domain Boost applies a specific boost for single-token candidates matching multi-token glossary entries. Category Starvation Prevention ensures balanced representation across glossary categories. Scoring Config Freeze centralizes all scoring weights, thresholds, and boost multipliers. Export Contract Hardening validates cached state completeness before building export payloads.

A Salesforce Resolver Stub (`server/resolvers/salesforce.py`) provides an interface contract for entity resolution. The OGC Preparation Simulator Operations View provides a multi-batch, DB-first governance queue, unifying patches, RFIs, and corrections into a single feed. Feature flags enable gradual migration to a PostgreSQL-backed Annotation Layer. The Verifier Organizational View provides a workspace-level governance dashboard with KPI summaries, batch queues, batch drill-downs, and a filter bar, guarded by RBAC. Verifier Triage Unification migrates this view into a canonical `#page-triage` frame, creating a role-adaptive interface.

Dark Mode v2 ("Subtle Futuristic Neon Control Panel") uses `ui/viewer/theme.css` as the single source of truth for all color tokens, supporting both light and dark modes. The toggle persists to localStorage. The Sidebar Icon System uses inline SVG icons with `currentColor` inheritance. A Collapsible Sidebar feature persists state to localStorage.

Google Drive Save (XLSX Export) supports hierarchical folder routing with per-member priority and automatic folder bootstrapping. The export filename format is `{batch_id}-{actor}-{status}-{timestamp}.xlsx`. The workbook structure includes DATA sheets, GOV_META, ACTIONS, STATE_JSON, and legacy sheets. Workspace drive folder settings are configurable via the Admin panel.

Field Suggestions UI upgrade adds collapsible section headers with per-section status pills, localStorage-based collapse persistence, right-click context menu for field cards, and dark mode CSS variable fixes. The CSV-backed Account Resolver provides 3-tier deterministic matching (exact → token overlap → edit distance) against `CMG_Account.csv` via `AccountIndex`.

Preflight Test Lab — Salesforce Match Integration wires the Salesforce account resolver into the preflight pipeline. The preflight engine uses `extract_account_candidates` with strict extraction logic and header fallback. The UI renders a matrix-style table with Source Text, Mapped Account, Match Status, Confidence, and Evidence columns, positioned after encoding findings.

Multi-Account Aware Composite Scoring adds context-aware scoring via `server/resolvers/context_scorer.py`. Each candidate gets a composite score based on name, address, account context, and service penalty. Multiple valid accounts are retained if they have sufficient evidence. Account-context boosts use two-tier cues (strong/weak). Proximity uses strict and soft windows. Service-context penalty is source-aware. Address evidence is candidate-local. Scoring tiers are defined for full/partial address verification. Match status mapping defines 'match', 'review', and 'no-match' based on composite score. The UI renders visible and hidden rows with chip color coding and a Debug toggle. Candidate extraction uses a hard denylist to suppress legal/common noise tokens unless extracted via strict label:value. Single-token uppercase words (≤6 chars) are also denied. Ranking sorts by source_type priority, then status, then confidence, then source alpha.

Resolution Story P0 adds `build_resolution_story()` to `server/preflight_engine.py`, producing a structured narrative from SF match results. CMG-side gating is a locked rule: `legal_entity_account` must be a CMG entity. If no CMG candidate passes threshold, `legal_entity_account = null` and `requires_manual_confirmation = true`. `counterparties[]` contains non-CMG candidates above a review threshold. Role selection is confidence-first within role constraints. `_guess_agreement_type()` uses a keyword-weighted heuristic. New Entry Detection (v2.57+): When CMG legal entity is resolved but a counterparty extracted from the contract party/recital block is not found in the Salesforce account index, the system sets `new_entry_detected=true`, populates `unresolved_counterparties[]`, and generates an `onboarding_recommendation` with suggested account name, type, and reason. The frontend shows a prominent "NEW ENTRY DETECTED" banner and a manual unresolved entry input. Party extraction uses `_extract_recital_parties()` with preamble-only parsing (first 35 lines): primary `between X and Y` regex + secondary `Name ("Role")` label regex.

Confidence Semantics (v2.57+): SF match results carry three confidence fields: `identity_confidence_pct` (normalized positive evidence — name + address + account context, clamped 0–100), `context_risk_penalty_pct` (penalty contribution in percent), and `final_confidence_pct` (composite-based percent). The UI match table displays Identity and Final on separate lines with a Risk badge when penalty > 0. Resolution Story entity cards show Final as primary percentage with Identity/Risk subtext when penalties apply. Section B reasoning includes a one-line confidence semantics explanation when any penalty exists. Backward compatibility: UI falls back to `confidence_pct` if new fields are missing. Resolver candidates are hard-capped at 24 to prevent backend stalls. Recital parties are extracted for story/new-entry detection only, not passed to the resolver for scoring. `_extract_recital_parties()` filters control chars, punctuation-only lines, colon labels, clause starts, and denylist tokens.

Deterministic Contract Classification (v2.58+): `server/data/preflight_contract_rules.v1.json` is the single source of truth for contract categories, expected schedule types, and termination flavors. `server/preflight_rules.py` evaluates the rules JSON deterministically, producing `contract_category`, `expected_schedule_types`, `termination_flavor` (with label and evidence), and `subtypes_allowed`. The `run_preflight()` payload includes a `contract_classification` object. Schedule Type detection (`_extract_schedule_type`) now suppresses `general_schedule` when rule-driven evidence supports a specific type. Priority ordering uses `schedule_type_priority` from the rules file. Subtype and schedule outputs are schema-locked to values defined in the rules JSON. Termination contracts support five flavors: mutual, for_cause, convenience, expiry, and reversion — detected via weighted keyword matching across title/preamble/body zones.

Patch Submit Modal (v2.57+) replaces the old Patch tab in the SRR sidebar with a centered modal dialog. The SRR left panel now has only two tabs: Edit and Info. After any action (field edit + Submit, RFI chip, Blacklist chip), a modal opens showing: patch type badge, context-appropriate summary, evidence fields for corrections, and a required justification textarea. The modal uses `_patchModalOpen`, `_patchModalClose`, `_patchModalConfirmSubmit`, and `_srrExecutePatchSubmit` functions. `srrBlacklistField` and `srrRfiField` auto-open the modal. `srrOnPatchTypeChange` opens the modal for RFI/Blacklist actions. A case-sensitivity fix in `canTransition()` normalizes role names to match `STATUS_TRANSITIONS` role arrays.

V2.58 Reconstruction Completion Gates wire the generate_copy → reconstruction_complete → override_red flow into the Contract Generator (cgb builder). `_pfGateState` tracks multi-step progression (`generateCopyDone`, `reconstructionCompleteDone`, `overrideRedDone`). `pfGateAction()` returns a Promise and accepts optional `extraPayload` for reconstruction_review. Gate panel rendering: GREEN passes immediately; YELLOW offers Accept Risk (instant unlock) or Generate Copy (requires reconstruction_complete before sync unlock); RED requires all three steps. `cgPageMarkReconstructionComplete()` collects clause review decisions from cgbState, builds a reconstruction_review payload with decisions, template_type, and fallback_note for NO_ENTITY_TEMPLATE_AVAILABLE, then calls pfGateAction('reconstruction_complete'). `cgbRenderGateStatus()` renders step-by-step progress in the cgb builder gate panel with action buttons for the current pending step. `srrCheckSyncPreflightGate()` enforces the new progression rules.

Resolver Data Feed (v2.56+): `server/routes/resolver_feed.py` exposes canonical Salesforce resolver datasets to the CGB frontend via `/api/v2.5/resolver/accounts` (paginated, searchable) and `/api/v2.5/resolver/accounts/summary`. The `AccountIndex` loads 14,385 accounts from `server/data/CMG_Account.csv`. Frontend functions `cgbFetchResolverAccounts()`, `cgbResolverAccountToRow()`, `cgbGetResolverRows()`, and `cgbHasResolverData()` cache and serve resolver records. CGB selectors (`buildSingleSelect`, `buildMultiSelect`) prefer resolver-sourced rows over workbook-derived rows; resolver values use `sf:` prefix (e.g., `sf:42`). `cgbBuildAnnotationMap` and `cgbSelectedRowsBySheet` handle resolver refs with `source: 'salesforce_resolver'` tagging. `cgbBuildBatchResolverIndex` incorporates resolver accounts into the legal entity typeahead. Currently only accounts have resolver backing; other object types (opportunity, schedule, catalog, v2 add-ons) continue using workbook rows.

Patch-to-Live (PTL) Pipeline (v2.59+): The PTL system provides a governed workflow for promoting analyst patch requests from sandbox to production. `srrCheckSyncPreflightGate()` enforces gate progression before patch submission. The PTL footer is simplified to show a single "Open Record" / "Open Annotation Layer" CTA when `RECORD_INSPECTOR_V2=true` — patch-submit buttons (Save Comment Draft, Submit Comment, Submit Correction) are moved into the workspace modal flow and removed from the PTL footer. State bridge (`_ptlStateBridge`) syncs gate state between the preflight test lab (`_pfGateState`) and the PTL pipeline (`_pftlState`). Check reason cells in all 4 section renderers (opportunity spine, schedule structure, SF match, encoding/quality) include actionable "Open in Inspector →" deep-links that call `pftlOpenWorkspaceV2(scope, checkCode)` for non-pass checks. The "Annotation Layer" tab button appears in the grid toolbar (alongside Review, Evidence Viewer, Suggestions, Preflight) instead of as a sidebar nav item.

Analyst Sandbox Triage Queue (v2.60+): The triage system includes a sandbox preflight queue (Queue 0) gated by `RECORD_INSPECTOR_V2`. `PREFLIGHT_TRIAGE_STORE` provides localStorage-backed CRUD (`orchestrate.preflight_triage_items` key) for sandbox preflight triage items with add/list/get/updateStatus/updateResult/remove/clear operations. Single PDF uploads via the toolbar auto-create triage items with gate color, health score, and check counts. A "Batch Preflight" toolbar button scans the `file_url` column from imported spreadsheets and queues items for async processing via `/api/preflight/run`. Progress UI shows a progress bar with per-item status (queued/running/done/failed) and a detail panel. Deep-link "Open in Inspector" buttons load stored preflight results into `_pfGateState` and open the workspace via `pftlOpenWorkspaceV2()`. The batch button auto-shows when a `file_url` column is detected during spreadsheet import.

V3 Unified Contract Workspace — Record Inspector V2 Beta (v2.60+): The unified workspace merges the Contract Generator, Preflight Test Lab, and Record Inspector into a single integrated view gated by `RECORD_INSPECTOR_V2` feature flag. Entry point: `pftlOpenWorkspaceV2(scope, checkCode)`. The workspace supports end-to-end flow: upload PDF → preflight gate → resolution story → contract generation → patch submission. Seven phases: (1) PTL deep-link with context payload, (2) focused section editor + evidence pane + change reason modal (10-char min reason, green gate attestation), (3) unmap/alias ingestion mapping controls, (4) canonical clause composer with live preview (entity_opportunity_resolution → asset_catalog_synchronization → financial_rights_modeling), (5) counterparty create flow with search/create dual mode, (6) domain-split permission matrix (ingestion: edit/unmap/alias/override; generation: compose/preview/draft) with CONTRACT_AUTHOR role, (7) patch submission aggregating all workspace state. 15 audit event types emitted via `_wsv2Audit()` → `AuditTimeline.emit()`. `RECORD_INSPECTOR_V2_DEFAULT` controls whether PTL edit targets workspace (true) or legacy CGB (false). `RECORD_INSPECTOR_V2_LEGACY_HIDDEN` reserved for v3.1 cutover.

## Tech Stack
- **Backend:** Python 3.11, FastAPI + Uvicorn (ASGI), PyMuPDF, openpyxl, playwright, psycopg2-binary, google-auth, rapidfuzz, sse-starlette, pytest
- **Database:** PostgreSQL 16 (Supabase-hosted), 13 migration files in `server/migrations/`
- **Frontend:** Vanilla JavaScript (no framework, no build step), single-file app at `ui/viewer/index.html` (~3.2 MB)
- **Styling:** `ui/viewer/theme.css` — CSS variable tokens for light/dark mode
- **Node.js:** Node 22 for `@redocly/cli` (OpenAPI linting) and verification scripts only
- **Integrations:** SheetJS (XLSX), Google Drive (workbook import/export), Google OAuth

## Run Configuration
The Replit "Project" button runs two workflows in parallel:
1. **Smoke Test:** `bash scripts/replit_smoke.sh` — validates config, runs deterministic preview, JSON-normalized diff vs expected output
2. **PDF Proxy:** `python -m uvicorn server.pdf_proxy:app --host 0.0.0.0 --port 5000` — CORS-safe PDF fetching + text extraction

Port 5000 maps to external port 80. Deployment target is `autoscale`.

## Testing
- **Smoke test:** `bash scripts/replit_smoke.sh` (baseline) or `bash scripts/replit_smoke.sh --edge` (edge cases) or `bash scripts/replit_smoke.sh --allow-diff` (skip JSON diff)
- **V3 parity test:** `bash scripts/v3_parity_test.sh` — 23 structural checks for V3 workspace parity
- **Unit tests:** `pytest tests/ -q --tb=short` — 437+ tests across 14 test files (use `--ignore=tests/test_suggestion_engine.py` if rapidfuzz missing)
- **Key test files:** `test_preflight_sf_match.py` (90KB), `test_preflight_opportunity_spine.py` (23KB), `test_custody_transitions.py` (21KB), `test_suggestion_engine.py` (19KB)

## Feature Flags
Set these environment variables before starting the server:
- `EVIDENCE_INSPECTOR_V251=true` — enables evidence inspector
- `PREFLIGHT_GATE_SYNC=true` — enables preflight gate synchronization
- `RECORD_INSPECTOR_V2=true` — enables V3 workspace, triage queue, PTL deep-links, annotation layer toolbar tab
- `RECORD_INSPECTOR_V2_DEFAULT=false` — when true, PTL edit targets workspace instead of legacy CGB
- `RECORD_INSPECTOR_V2_LEGACY_HIDDEN` — (reserved for v3.1) hides legacy nav items after cutover

Flag cache: flags cached on first read in `server/feature_flags.py`. Restart server or call `feature_flags.clear_cache()` to pick up changes.

## Key File Paths
| File | Purpose |
|---|---|
| `ui/viewer/index.html` | Entire frontend (~3.2 MB single-file vanilla JS app) |
| `ui/viewer/theme.css` | CSS token system (light/dark mode) |
| `server/pdf_proxy.py` | FastAPI entry point — PDF proxy + text extraction + feature flags endpoint |
| `server/preflight_engine.py` | Core preflight logic (85KB) |
| `server/preflight_rules.py` | Deterministic rule evaluator |
| `server/suggestion_engine.py` | Heuristic field suggestions (34KB) |
| `server/feature_flags.py` | V3 feature flag constants + helpers |
| `server/auth.py` | Role enum (ANALYST, VERIFIER, ADMIN, ARCHITECT, CONTRACT_AUTHOR) + RBAC |
| `server/resolvers/context_scorer.py` | Multi-account composite scoring |
| `server/data/CMG_Account.csv` | 14,385 Salesforce account records |
| `config/config_pack.base.json` | Authoritative base semantics ("Truth Config") |
| `scripts/v3_parity_test.sh` | 23-check V3 workspace validation gate |
| `scripts/replit_smoke.sh` | Baseline + edge-case smoke tests |

## Sandbox Session Reset
If the app gets into a bad state, run this in the browser console:
```js
localStorage.removeItem('orchestrate_session');
localStorage.removeItem('orchestrate_preflight_state');
localStorage.removeItem('orchestrate.preflight_triage_items');
location.reload(true);
```

## External Dependencies
- **FastAPI server**: Used as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF.
- **SheetJS (XLSX)**: Integrated for Excel import/export functionality.
- **Google Drive**: Integrated as a data source for contract workbook import/export, with role-based folder routing for XLSX exports.