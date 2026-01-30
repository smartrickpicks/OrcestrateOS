# Kiwi Semantic Control Board (v1.3.0)

## Overview

This repository is a **governance-only semantic control plane** for DataDash + Kiwi. It defines, validates, and previews semantic rules offline so decisions are explicit, deterministic, and auditable.

**Core Purpose:**
- Single source of semantic truth: rules, templates, examples, and governance documents
- Offline harness to validate and preview semantics deterministically
- Rule authoring and review as configuration (not code)
- Analyst-first reference with clear interfaces and checklists

**v1.2 Dashboard Shell:**
- Queue-centric sidebar: To Do, Needs Review, Flagged, Blocked, Finalized with live counts
- Right-side drawers: Data Sources Drawer, Record Detail Drawer
- Role-based navigation: Analyst (default), Verifier, Admin
- Session management: Data Sources, Evidence Status, Reset Session
- First-Run Configure Wizard: Multi-step setup for data sources and workflow defaults
- Admin Config Flows: Workflow-ordered view of config artifacts with Plain-English, Payload, Master tabs

**v1.2.1 Phase 2 Features (D1-D4):**
- D1 Masterline Autoload: Dev toggle in Admin, artifact registry with Loaded/Missing status chips, localStorage persistence
- D2 Admin Workflow Map: 8-stage vertical pipeline with clickable nodes (Load Data → PR Ready)
- D3 Standardizer: CSV parsing with delimiter inference, header normalization, merged_dataset.json output, error model
- D4 Tooltips & Plain English: NOMENCLATURE maps, info icons with tooltips, humanLabel()/getTooltip() helpers

**v1.2.2 Patch Queue as Admin Status Pipeline:**
- Comment (RFI) System: 5-status lifecycle (Open → Resolved → ElevatedToPatchRequest), localStorage persistence
- Patch Request Pipeline: 11-status lifecycle with Kiwi handshake (SentToKiwi → KiwiReturned → Applied)
- Admin Patch Console: 7 queue tabs with live counts, batch selection, export/import actions
- Patch Request Detail Drawer: Plain-English Intent, Kiwi Payload viewer, Apply Checklist
- Comment UI: Add Comment modal, Elevate to Patch Request flow, Comments panel in Record Drawer

**v1.2.3 Patch Studio + Role-Gated Review Pipeline:**
- Role-Based Access Control: Analyst, Verifier, Admin with permission gating
- Extended 12-status lifecycle: Needs_Clarification, Reviewer_Responded, Admin_Hold
- Patch Studio as Workbench Tab: Draft, Preflight, Evidence Pack sub-tabs
- Submit to Patch Queue CTA with audit logging
- Preflight Checks with pass/warn/fail badges and Copy Report
- Evidence Pack: 4 structured blocks (Observation, Expected, Justification, Repro)
- Verifier Actions: Request Clarification, Approve, Reject, Review Notes
- Admin Actions: Admin Approve, Admin Hold, Export to Kiwi, Paste Return, Mark Applied
- Revision Tracking: revisions array with diff summaries and snapshots
- Append-only Audit Log with event types

**v1.2.4 Structured Intent + UI Cleanup:**
- Structured Intent Authoring: Target Field selector, Condition Type dropdown, Action Type dropdown
- "Other" escape hatch for edge cases with custom text input
- Live Intent Preview showing rendered WHEN/THEN/BECAUSE
- Updated PatchRequestV1 schema with intent_structured and intent_rendered fields
- Form validation with required fields and character limits
- Removed legacy Patch Studio overlay panel (no more stacked drawers)

**v1.2.5 Loader + Testability:**
- Loader as first-class nav item (top of sidebar, "Start" section)
- Loader page: Load Sample Dataset, Import CSV/XLSX, Attach PDF
- Deterministic sample dataset (examples/datasets/sample_v1.json) with one-click load
- Test Utilities: Reset Demo State, Rebuild Field Index
- Dataset summary card after load with CTA to Spreadsheet View
- CSV import with delimiter inference and header normalization

**v1.3.0 UI-ADMIN-ENTITY-SEPARATION:**
- Hard page separation: navigateTo() properly hides all pages before showing target (no bleed-through)
- RBAC route guards: Non-admin redirected to triage with toast notification
- Admin section markers: data-admin-section="true" for smoke test assertions
- Dev-only assertion: console.error if admin sections found in triage DOM
- Page labels: Explicit route context (PAGE: TRIAGE, PAGE: ADMIN-GOVERNANCE, etc)

**What This Is NOT:**
- Not a runtime system
- Not connected to any external APIs
- Not a store for credentials, secrets, or endpoints
- Not a place for LLM prompts or prompt engineering
- No DataDash pipeline, Salesforce integration, extraction, resolution, or enrichment logic

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Repository Structure

| Directory | Purpose |
|-----------|---------|
| `docs/` | Operator-facing documentation and governance (start with `docs/INDEX.md`) |
| `rules/` | Analyst-friendly rule authoring templates (Salesforce, QA, Resolver) |
| `config/` | Semantic config base + patch files (no credentials) |
| `examples/` | Synthetic sample data for offline preview |
| `local_runner/` | Offline validation and preview tools |
| `scripts/` | Utility scripts (MCP link generation, smoke tests) |
| `ui/` | Placeholder UI skeleton (non-executing) |

### Core Design Decisions

**1. Governance-Only Control Plane**
- All semantic decisions are captured as reviewable configuration artifacts
- No runtime execution, no APIs, no credentials, no prompts
- Changelog documents "why" changes were made, not just "what"

**2. Offline-First Determinism**
- Same inputs must produce identical outputs
- All previews run locally without network access
- Stdlib-only Python (no external dependencies)

**3. Join Strategy**
- Canonical join order: `contract_key` → `file_url` → `file_name`
- No fabricated identifiers
- Unmatched cases surface as explicit issues

**4. Config Pack Model**
- `config_pack.base.json`: Versioned baseline semantic model
- `config_pack.patch.json`: Changes array (`add_rule`, `deprecate_rule`)
- Patch `base_version` must exactly match base `version`

### Key Commands

**Validate configuration:**
```bash
python3 local_runner/validate_config.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json
```

**Run deterministic preview:**
```bash
python3 local_runner/run_local.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json \
  --standardized examples/standardized_dataset.example.json \
  --out out/sf_packet.preview.json
```

**Smoke test (required before PRs):**
```bash
bash scripts/replit_smoke.sh
```

### Rule Schema

Rules follow a WHEN/THEN pattern:
- `rule_id`: Unique identifier (e.g., `SF_R1_LABEL_NOT_ARTIST`)
- `when`: Condition with `sheet`, `field`, `operator`, `value`
- `then`: Actions with `action`, `sheet`, `field`, `severity`

Allowed operators: `IN`, `EQ`, `NEQ`, `CONTAINS`, `EXISTS`, `NOT_EXISTS`
Allowed actions: `REQUIRE_BLANK`, `REQUIRE_PRESENT`, `SET_VALUE`
Severity levels: `info`, `warning`, `blocking`

### Output Format

Preview generates `sf_packet` with:
- `sf_summary`: Contract counts by status (ready/needs_review/blocked)
- `sf_contract_results`: Per-contract status and subtype
- `sf_field_actions`: Rule-triggered field actions
- `sf_issues`: Detected problems

## External Dependencies

**None by design.** This repository uses Python standard library only.

- No external Python packages (see `requirements.txt`)
- No database connections
- No API integrations
- No runtime services
- No credentials or secrets

The repository is intentionally isolated as a governance-only control plane, separate from any execution environments.