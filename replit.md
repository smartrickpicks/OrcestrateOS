# Orchestrate OS — Semantic Control Board

## Overview
Orchestrate OS is a governance-only semantic control plane designed to define, validate, and preview semantic rules offline. It acts as a single source of semantic truth, enabling rule authoring and review as configuration. The project aims to improve operator ergonomics, streamline the patch request and review pipeline, and provide an analyst-first reference with clear interfaces for explicit, deterministic, and auditable decisions. It captures semantic decisions as reviewable configuration artifacts and operates offline-first, ensuring deterministic outputs using only the Python standard library for local previews.

## User Preferences
Preferred communication style: Simple, everyday language.

## System Architecture
The core design involves capturing semantic decisions as reviewable configuration artifacts. Data handling employs a canonical join strategy (`contract_key` → `file_url` → `file_name`) and a Config Pack Model (`config_pack.base.json` for baseline, `config_pack.patch.json` for changes) with strict version matching. The system supports an 11-status lifecycle for patch requests, including comment systems and role-based access control (Analyst, Verifier, Admin).

The UI features a dashboard with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are presented in a workflow-ordered view with Plain-English, Payload, and Master tabs. A Patch Studio enables drafting, preflight checks, and evidence packing with live previews and revision tracking. UI elements include color-coded grid highlighting, Excel-style column headers with drag-and-drop reordering, and a PDF viewer. Record Inspection (SRR) provides navigation and auto-advances.

Data handling supports CSV/XLSX import, a Field Inspector for search-filtered fields, inline editing, and a lock-on-commit mechanism. A change map engine tracks cell-level changes, propagating entries to canonical stores. The Verifier Triage uses a 4-queue system, and a localStorage-backed mock filesystem manages artifacts. Workbook session caching persists uploaded Excel data to IndexedDB, supporting multi-session storage and auto-save.

Semantic rules generate deterministic cell-level signals on dataset load using `field_meta.json` and `qa_flags.json` for validation, populating Analyst Triage queues and driving grid coloring. Rules follow a WHEN/THEN pattern. Record identity is defined by `tenant_id`, `division_id`, `dataset_id`, `record_id`. The system uses email-based access control with Google sign-in for production OAuth.

Features include "Catalog Items Group" for batch adding and deduplication, and a `_document_type` and `_capabilities` object per record, with document types loaded from `config/document_types.json`. Export functionality generates XLSX files including all data sheets, change logs, signals summaries, and metadata. An Audit Timeline system uses an IndexedDB-backed store for all governance actions, accessible via a UI with filtering options and exportable to XLSX.

The system incorporates a Schema Tree Editor for managing the canonical rules bundle, including `field_meta.json`, `hinge_groups.json`, `sheet_order.json`, `qa_flags.json`, `document_types.json`, and `column_aliases.json`. It supports column alias resolution and tracking of schema changes. A Batch Merge feature allows combining source batches into a single governance container, with explicit rule promotion for tenant rules.

Document roles (`Root Agreement`, `Amendment`, etc.) are distinct from document types and are inferred with user confirmation. A `SystemPass` module provides a deterministic, rerunnable, proposal-only engine for system changes, routed to a "System Changes" triage bucket. Pre-Flight triage buckets handle blockers like unknown columns or unreadable OCR. A Contract Index Engine builds a hierarchy of batch→contract→document→sheet→row, persisting summary references to SessionDB.

### Hinge-Governed Apply + Undo vs Rollback (v2.2 P1)
`SystemPass.acceptProposal()` for hinge-field proposals auto-creates a `system_suggested` patch artifact in `PATCH_REQUEST_STORE` and routes through the standard patch lifecycle (Draft → Submitted → Verifier → Admin → Applied). Non-hinge proposals remain directly acceptable. Emits `system_change_routed_to_patch` audit event.

`UndoManager` provides local, session-scoped undo for draft-only SRR inline edits. Window-based buffer (5 min / 50 entries max). Cannot undo approved/submitted artifacts. Emits `undo_local` audit event. Wired into `FIELD_CORRECTED` flow.

`RollbackEngine` creates governed rollback artifacts at 4 scopes (field, patch, contract, batch). Two-phase flow: `createRollback()` → `rollback_created` event, then `applyRollback()` → `rollback_applied` event. Append-only — never deletes history; captures before/after state snapshots. References original event/artifact IDs.

Rollback-triggered rerun: If `applyRollback()` detects hinge-field modifications, auto-calls `SystemPass.run('rollback_hinge_affected')` and renders new proposals.

Audit alignment: `undo_local`, `rollback_created`, `rollback_applied`, `system_change_routed_to_patch` registered in `_canonicalAuditEventName` aliases, `AUDIT_TYPE_CATEGORIES.rollback`, `_inferAuditScope`, and audit filter dropdown ("Undo / Rollback"). Docs: `docs/UNDO_VS_ROLLBACK.md`.

### Final Polish + Release Hardening (v2.2 P2)
System Changes UX: bulk reject with reason (`SystemPass.bulkReject()`), confidence sort/filter presets, hinge-required badge with "must route via patch" explanation tooltip. Pre-Flight clarity: 4 blocker types (UNKNOWN_COLUMN, OCR_UNREADABLE, LOW_CONFIDENCE, MOJIBAKE) with severity badges and `createPatchFromBlocker()` one-click governed patch creation. Audit panel polish: saved filter presets (localStorage), quick chips for system_change/rollback/schema_change/session categories, live header-to-panel sync on event emission. Export consistency: audit-only export uses stable column ordering (event_id, timestamp, event_type, subtype, actor_role...) with payload_summary truncation at 200 chars and full artifact_refs; full export includes batch_id, contract_id, document_id, document_type, document_role, capabilities, merged_from. Docs hardening: 6 files updated for V2.2 terminology (Pre-Flight, System Pass, Verifier, proposal-only, governed rollback). Export version bumped to v2.2-P2.

### Triage Analytics Header (v2.3)
`TriageAnalytics` module aggregates metrics from existing stores (analystTriageState, SystemPass._proposals, PATCH_REQUEST_STORE, ContractIndex, rulesBundleCache) into a lightweight cache with no data duplication. Renders above the triage grid with: 3-lane cards (Pre-Flight, Semantic, Patch Review) with click-through filtering; horizontal lifecycle tracker (9 stages: Loaded → Applied) with contract-level counts/percentages; contract summary drilldown table with lane alert counts and row-click navigation; schema snapshot block showing field match %, unknown columns, missing required, schema drift. Hidden by default, shown after data load via `renderAnalystTriage()`. Refreshed on dataset load, System Pass rerun, proposal accept/reject, patch submit/promote, rollback apply.

### Record Inspector Guidance (v2.3b)
Section guidance card rendered at top of SRR Field Inspector with collapsible "What to look for" and "Common failure modes" checklists. Config loaded from `config/section_guidance.json`, keyed by `document_role::document_type` with fallback chain. Expand/collapse preference persisted to localStorage. Re-rendered deterministically on each field list rebuild via `renderSrrFields()` and on SRR record navigation via `srrRefreshGuidanceAndRail()`. Knowledge rail panel in SRR right panel shows role-filtered links from `config/knowledge_links.json` with external-link icons and `knowledge_link_opened` audit event.

## External Dependencies
A FastAPI server acts as a local PDF proxy for CORS-safe PDF fetching and text extraction using PyMuPDF. SheetJS (XLSX) is loaded via CDN for Excel import/export functionality.