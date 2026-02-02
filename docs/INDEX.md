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
- docs/ui/views/record_inspection_view.md
- docs/ui/views/patch_authoring_view.md
- docs/ui/views/verifier_review_view.md
- docs/ui/views/admin_approval_view.md
- docs/ui/views/promotion_view.md
- docs/ui/views/data_source_view.md
- docs/ui/views/all_data_grid_view.md
- docs/ui/views/single_row_review_view.md

## Rules and Templates
- rules/salesforce_rules.txt
- rules/qa_rules.txt
- rules/resolver_rules.txt

## Config Templates
- config/config_pack.base.json
- config/config_pack.example.patch.json

## Examples and Preview
- examples/README.md
- examples/standardized_dataset.example.json
- examples/expected_outputs/qa_packet.example.json
- examples/expected_outputs/sf_packet.example.json
- local_runner/README.md

## Replit Tools (Optional)
- docs/07_replit_mcp.md — Replit MCP operator guide and install-link format
- scripts/mcp_link_gen.py — deterministic MCP install-link generator (ENCODED, LINK, BADGE_MARKDOWN)
- scripts/replit_smoke.sh — strict diff smoke test (exit 1 on mismatch; `--allow-diff` to override)
- .replit — one-button run (validate then preview)
- requirements.txt — explicit stdlib-only intent
