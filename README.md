# kiwi-semantic-control

## Purpose
This repository is the governance-only semantic control plane for DataDash + Kiwi. It defines, validates, and previews semantic rules offline so decisions are explicit, deterministic, and auditable.

## What This Repo Is
- A single source of semantic truth: rules, templates, examples, and governance documents
- A place to author and review rule changes as configuration (not code)
- An offline harness to validate and preview semantics deterministically
- An operator-first reference with clear interfaces and checklists

## What This Repo Is Not
- Not a runtime system
- Not connected to any external APIs
- Not a store for credentials, secrets, or endpoints
- Not a place for LLM prompts or prompt engineering
- Not a DataDash pipeline, Salesforce integration, extraction, resolution, or enrichment logic

## Repository Structure
- docs/ — operator-facing documentation and governance
  - docs/INDEX.md — primary navigation entry for operators and reviewers
  - Scope, architecture, lifecycle, interfaces, truth snapshot, conflict resolution, review checklist
- rules/ — analyst-friendly rule authoring templates (Salesforce, QA, Resolver)
- config/ — semantic config base + patch files (no credentials)
  - config_pack.base.json — canonical base configuration (versioned)
  - config_pack.example.patch.json — example patch format (changes[])
- examples/ — synthetic sample data for offline preview
  - standardized_dataset.example.json — minimal sheeted dataset exercising join strategy
  - expected_outputs/ — example preview outputs
- local_runner/ — offline validation and preview tools
  - validate_config.py — shape checks and conflict detection
  - run_local.py — deterministic preview to an sf_packet-like JSON
- CHANGELOG.md — governance changes and rationale

## Offline Quickstart
Prerequisites: Python 3. No network access required.

1) Validate configuration
```
python3 local_runner/validate_config.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json
```

2) Run a deterministic preview (base + patch) on the standardized dataset
```
python3 local_runner/run_local.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json \
  --standardized examples/standardized_dataset.example.json \
  --out out/sf_packet.preview.json
```

3) (Optional) Include a QA packet for traceability (not used in rule logic; recorded in sf_meta)
```
python3 local_runner/run_local.py \
  --base config/config_pack.base.json \
  --patch config/config_pack.example.patch.json \
  --standardized examples/standardized_dataset.example.json \
  --qa examples/expected_outputs/qa_packet.example.json \
  --out out/sf_packet.preview.json
```

Determinism: Given identical inputs, outputs are identical. No external calls are made.

## Governance Workflow (High Level)
1) Discover a pattern or issue during review
2) Draft a rule in plain English (rules/salesforce_rules.txt guidance)
3) Encode the rule as a patch (config/config_pack.example.patch.json) using changes[] (add_rule/deprecate_rule)
4) Validate offline (validate_config.py)
5) Preview offline (run_local.py) and inspect out/sf_packet.preview.json
6) Submit a PR with rationale and example results; update CHANGELOG.md
7) Reviewers apply docs/REVIEW_CHECKLIST.md before approval

Join strategy (global): contract_key → file_url → file_name. No fabricated identifiers.

## How This Integrates with DataDash (Conceptual Only)
- DataDash (or other runtimes) consume exported semantic configs created here
- This control board defines canonical meaning; runtime behavior does not alter semantic truth
- When runtime behavior diverges, propose a new patch through the governance process; do not change prior truth retroactively

Primary navigation: see docs/INDEX.md.

## Control Board Viewer (v1.1)

A single-file, zero-dependency HTML viewer for sf_packet artifacts. See `ui/viewer/README.md` for details.

**Features:**
- **v1.1**: Upload-First Flow + Modal Wizards (Load Data CTA, triage-first landing)
- **v1.0**: Multi-Page Navigation + Mode Toggle (Run/Triage/Patch Studio/Review pages)
- **v0.9**: Session + Stream Model (conceptual streaming semantics, record states, reconsolidation rules)
- **v0.8**: Config + Patch Inspector (ruleset loader, version match, changes table)
- **v0.7**: Comparison Mode (delta summary, row-level change indicators)
- **v0.6**: Preflight Gate (4-step validation checklist)
- **v0.5**: Patch Studio Lite (selectable records, grouped rule builder)
- **v0.4**: Universal drilldown, Copy PR Kit
- **v0.3**: Record Workbench with tabbed drawer

**Open in browser:**
```
# Replit: see Webview panel
# Local: python3 -m http.server 5000 && open http://localhost:5000/ui/viewer/index.html
```

### Smoke Test Verification
After running `bash scripts/replit_smoke.sh`, compare `out/sf_packet.preview.json` against `examples/expected_outputs/sf_packet.example.json`. Any differences must be resolved (code determinism/schema) or justified (update expected output + changelog).

### Replit MCP (optional)
See docs/07_replit_mcp.md for how to:
- Generate a deterministic install link payload (scripts/mcp_link_gen.py)
- Install MCP in Replit
- Run the smoke flow (scripts/replit_smoke.sh) or the .replit run command
