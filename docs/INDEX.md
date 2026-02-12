# INDEX (Operator-First Table of Contents)

## Start Here (3 Steps)
1) Read the system overview and scope
   - docs/00_system_overview.md
   - docs/SCOPE_control_plane.md
2) Understand architecture, lifecycle, and interfaces
   - docs/CONTROL_BOARD_ARCHITECTURE.md
   - docs/RULE_LIFECYCLE.md
   - docs/INTERFACES.md
3) Prepare a change
   - rules/salesforce_rules.txt (author a new rule)
   - config/config_pack.example.patch.json (place your patch)
   - local_runner/README.md (run an offline preview)

---

## Core Explainers (00–06)
- docs/00_system_overview.md
- docs/01_workflow_flow_explainer.md
- docs/02_resolver_salesforce_matching_explainer.md
- docs/03_confidence_scoring.md
- docs/04_subtype_schema_matrix.md
- docs/05_operator_validator_sop.md
- docs/06_how_to_add_rules.md

## Decision Memos (V2.2+)
- docs/memos/INDEX.md — Memo index with purpose and version
- docs/memos/V23_GATE_DECISIONS.md — G1–G9 locked gate rules (derivation, rebuild, thresholds, routing, sanitization, storage, selector, orphan, payload)
- docs/memos/V23_MODE_SPLIT.md — Production vs Sandbox mode split, permission gates, Admin role scope
- docs/memos/V23_ID_MODEL.md — Identity model: Tenant → Contract → Document → Record; ID derivation and contract_id_source
- docs/decisions/DECISION_HIERARCHY.md — Batch→contract→document→contract section→row hierarchy and rebuild policy
- docs/decisions/DECISION_ID_EXTRACTION.md — ID extraction priority, URL canonicalization, orphan policy
- docs/decisions/DECISION_UNKNOWN_COLUMNS.md — Unknown column thresholds, frequency-vote attachment, audit payload
- docs/decisions/DECISION_STORAGE_POLICY.md — localStorage vs IndexedDB payload policy
- docs/decisions/DECISION_SANDBOX_PRODUCTION.md — Sandbox (permissionless) vs Production (strict gates) split
- docs/UNDO_VS_ROLLBACK.md — Undo (local, session-scoped) vs Rollback (governed, append-only)
- config/id_extraction_rules.json — Machine-readable ID extraction and URL canonicalization rules

## V2.3 Release Readiness
- docs/V23_GATE_VERIFICATION_RUNBOOK.md — Deterministic verification steps for G1–G9 gates
- docs/V23_RELEASE_CHECKLIST.md — Pre-flight checklist, regression checklist, ship/no-ship signoff
- docs/V23_NAV_MAP.md — Quick-reference: where to find gate policy, mode split, audit contract, verification, signoff

## Governance Docs (Scope-Locked)
- docs/SCOPE_control_plane.md
- docs/CONTROL_BOARD_ARCHITECTURE.md
- docs/RULE_LIFECYCLE.md
- docs/INTERFACES.md
- docs/TRUTH_SNAPSHOT.md
- docs/CONFLICT_RESOLUTION.md
- docs/REVIEW_CHECKLIST.md
- docs/AUDIT_LOG.md

## V1 Workflow & Doctrine
- docs/V1/Flow-Doctrine.md

## UI Contracts
- docs/ui/ui_principles.md
- docs/ui/gate_view_mapping.md

### UI Roles
- docs/ui/roles/analyst.md
- docs/ui/roles/verifier.md
- docs/ui/roles/admin.md

### UI Views
- docs/ui/views/triage_view.md
- docs/ui/views/patch_authoring_view.md
- docs/ui/views/verifier_review_view.md
- docs/ui/views/admin_approval_view.md
- docs/ui/views/promotion_view.md
- docs/ui/views/data_source_view.md
- docs/ui/views/all_data_grid_view.md
- docs/ui/views/single_row_review_view.md

## Ingestion & Data Pipeline
- docs/ingestion/DATA_LOADER_PIPELINE.md — End-to-end Excel upload, parsing, caching, signal generation, and future Google Drive plans
- docs/ingestion/INGESTION_DOCTRINE.md — Folder conventions and attribution patterns

## Rules and Templates
- rules/salesforce_rules.txt
- rules/qa_rules.txt
- rules/resolver_rules.txt
- docs/rules/rules_bundle.md — Rules Bundle overview and regeneration guide

## Config Templates
- config/config_pack.base.json
- config/config_pack.example.patch.json

## Examples and Preview
- examples/README.md
- examples/standardized_dataset.example.json
- examples/expected_outputs/qa_packet.example.json
- examples/expected_outputs/sf_packet.example.json
- local_runner/README.md

## Feature Requests
- docs/features/STANDARDIZER_SCHEMA_EDITOR.md — Schema Tree Editor for Admin Standardizer tab (V2 proposal)

## API v2.5 (Gate 3 Complete — Ready for Code)
- docs/handoff/V25_READINESS_REPORT.md — V2.5 readiness audit: Done/Partial/Missing matrix with file paths, line refs, risk levels
- docs/decisions/DECISION_V25_DB.md — PostgreSQL canonical DB decision lock
- docs/api/API_SPEC_V2_5_CANONICAL.md — Human-readable API contract: 14 resource schemas, transition matrix, RBAC, envelopes, concurrency
- docs/api/openapi.yaml — OpenAPI 3.1 spec for /api/v2.5/ endpoints
- docs/api/asyncapi.yaml — SSE event envelope and topic definitions
- docs/handoff/V25_TASK_LIST.md — Dependency-aware task list across all 5 gates
- docs/handoff/V25_CLARITY_MATRIX.md — Gate 2 clarity matrix: resolved Q1 (auth), Q2 (workspace isolation), contradictions
- docs/handoff/V25_LOCKED_DECISIONS.md — 11 frozen decisions with canonical text and change request process
- docs/handoff/V25_FINAL_TASK_PLAN.md — Gate 3 frozen task plan: 30 tasks, 4 phases, acceptance criteria, sequencing
- docs/handoff/V25_CONTRACT_LOCK.md — Contract lock summary: what is frozen, what is flexible, CR process
- docs/handoff/V25_GATE3_ALIGNMENT_PACKET.md — Consolidated Gate 3 alignment artifact: task plan table, sequencing lock, contract freeze, test plan, risk register, GO request

## Handoff & Status
- docs/handoff/srr-handoff-status.md — Record Inspection handoff documentation audit (v1.5.2)
- docs/handoff/TASKS_UI.md — UI backlog tracker
- docs/handoff/STATUS.md — General status
- docs/handoff/HANDOFF.md — Handoff guide

## AppModules Architecture
- docs/architecture/appmodules-catalog.md — Full module catalog: 55 modules across 16 phases (C, D1–D15) with delegate sites and deterministic logs
- docs/architecture/appmodules-map.md — Mermaid dependency graph showing Engines, Components, and cross-phase call paths
- docs/architecture/appmodules-index.md — Developer guide: safe calling patterns, adding new modules, extraction checklist, ES5 compliance

## Replit Tools (Optional)
- docs/07_replit_mcp.md — Replit MCP operator guide and install-link format
- scripts/mcp_link_gen.py — deterministic MCP install-link generator (ENCODED, LINK, BADGE_MARKDOWN)
- scripts/replit_smoke.sh — strict diff smoke test (exit 1 on mismatch; `--allow-diff` to override)
- .replit — one-button run (validate then preview)
- requirements.txt — explicit stdlib-only intent
