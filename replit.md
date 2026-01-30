# Kiwi Semantic Control Board (v1.2)

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
- Role-based navigation: Analyst (default), Reviewer, Admin
- Session management: Data Sources, Evidence Status, Reset Session

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