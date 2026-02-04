# Orchestrate OS — Semantic Control Board

## Overview

Orchestrate OS is a governance-only semantic control plane for DataDash + Kiwi, designed to define, validate, and preview semantic rules offline. Its core purpose is to serve as a single source of semantic truth, enabling rule authoring and review as configuration rather than code. It aims to provide an analyst-first reference with clear interfaces and checklists, ensuring explicit, deterministic, and auditable decisions. The project focuses on improving operator ergonomics and streamlining the patch request and review pipeline.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Repository Structure

The repository is organized into `docs/` for documentation, `rules/` for rule authoring templates, `config/` for semantic configuration, `examples/` for synthetic data, `local_runner/` for offline validation tools, `scripts/` for utilities, and `ui/` for the user interface skeleton.

### Core Design Decisions

1.  **Governance-Only Control Plane**: All semantic decisions are captured as reviewable configuration artifacts, with no runtime execution, APIs, credentials, or prompts.
2.  **Offline-First Determinism**: Ensures identical outputs for the same inputs, with all previews running locally without network access, using only the Python standard library.
3.  **Join Strategy**: Employs a canonical join order (`contract_key` → `file_url` → `file_name`) without fabricating identifiers, explicitly surfacing unmatched cases.
4.  **Config Pack Model**: Utilizes `config_pack.base.json` for the versioned baseline semantic model and `config_pack.patch.json` for changes, with strict version matching.
5.  **UI/UX**: Features a dashboard shell with a queue-centric sidebar, right-side drawers for data sources and record details, and role-based navigation. Admin configurations are presented in a workflow-ordered view with Plain-English, Payload, and Master tabs. The system includes extensive tooltips and Plain English explanations derived from nomenclature maps.
6.  **Patch Request Pipeline**: Implements a robust 11-status lifecycle for patch requests, including comment systems, role-based access control (Analyst, Verifier, Admin), and a Patch Studio for drafting, preflight checks, and evidence packing. It includes structured intent authoring with live previews and revision tracking with audit logging.
7.  **Data Loading and Testing**: Features a dedicated loader for sample datasets, CSV/XLSX import with delimiter inference, and utilities for resetting demo state and rebuilding field indexes.
8.  **UI-ADMIN-ENTITY-SEPARATION**: Enforces hard page separation, RBAC route guards, and explicit page labels for clear navigation and security.
9.  **DataDash V1 Operator Ergonomics**: Introduces an All-Data Grid for a dense spreadsheet view, deterministic filtering, and a consistent entry point for single-row review.
10. **PDF Proxy and Field Resolution**: Utilizes a FastAPI PDF proxy for CORS-safe PDF fetching and `srrResolveFieldValue()` for Salesforce-style column resolution, with security guards and size limits.
11. **Field Inspector and Patch Editor**: Provides search-filtered fields, inline editing, a lock-on-commit mechanism for changed fields, and a restructured Evidence Pack with dropdown selectors and optional notes.
12. **Verifier Triage and Payload System**: Offers a 4-queue system for verifiers, automatic view swapping based on roles, and type-specific content blocks for reviews. v1.5.2 adds division + status filter bars with localStorage persistence, shared filter state between Triage and Grid, status-based row highlighting (yellow=pending, orange=clarification, blue=sent_to_admin, green=resolved), and proper routing via patch_request_id to Verifier Review.
13. **Artifact Store and Role Handoff Routing**: Uses a localStorage-backed mock filesystem for artifacts, a deterministic artifact ID system, event logging, and a thread system for conversations. It supports playground mode with environment scoping and a seamless handoff from Verifier Approval to the Admin Patch Queue.
14. **Record Identity Model**: Defines `tenant_id`, `division_id`, `dataset_id`, `record_id` as first-class identity fields, with source pointers and aliases, and generates `record_id` based on a canonicalized row fingerprint.
15. **SRR Hydration**: Ensures proper hydration of Single Row Review (SRR) by loading PatchRequests from a shared `localStorage` store before loading record data.
16. **Reviewer SRR Mode (v1.5.3)**: When reviewers click "Open Record" from Verifier Review, they enter a read-only Reviewer SRR with: left panel showing Field Inspector (editing disabled via isReadOnly flag), right panel with Patch Review + Patch Tester tabs. Patch Tester is hidden for RFI type, showing comment thread instead. Division filter now includes "Unassigned" bucket for items without division_id. Patch type tabs (Corrections, Blacklist, RFI) added to Reviewer Triage for grouping. Reviewer mode is automatically reset when navigating away from SRR.

### Key Commands

-   **Validate configuration**: `python3 local_runner/validate_config.py --base config/config_pack.base.json --patch config/config_pack.example.patch.json`
-   **Run deterministic preview**: `python3 local_runner/run_local.py --base config/config_pack.base.json --patch config/config_pack.example.patch.json --standardized examples/standardized_dataset.example.json --out out/sf_packet.preview.json`
-   **Smoke test**: `bash scripts/replit_smoke.sh`

### Rule Schema

Rules follow a WHEN/THEN pattern with `rule_id`, `when` conditions (sheet, field, operator, value), and `then` actions (action, sheet, field, severity). Allowed operators include `IN`, `EQ`, `NEQ`, `CONTAINS`, `EXISTS`, `NOT_EXISTS`. Actions include `REQUIRE_BLANK`, `REQUIRE_PRESENT`, `SET_VALUE`. Severity levels are `info`, `warning`, `blocking`.

### Output Format

The preview generates an `sf_packet` containing `sf_summary` (contract counts), `sf_contract_results` (per-contract status), `sf_field_actions` (rule-triggered actions), and `sf_issues` (detected problems).

## External Dependencies

None by design. This repository exclusively uses the Python standard library. It has no external Python packages, database connections, API integrations, runtime services, or credentials/secrets.