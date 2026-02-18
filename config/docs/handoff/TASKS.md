# TASKS (Handoff)

Audience: Governance verifiers and operators
Purpose: Enumerate governance-aligned tasks with evidence references
Scope: Docs-only; no runtime or implementation tasks
Non-Goals: Do not claim code merges or runtime changes
Authority Level: Informational; tasks must reference evidence links
Owner Agent: Documentation architect (Orchestrate OS)
Update Rules: Every task must include a source link; unresolved items must name an owner and required evidence source

Repository: Orchestrate OS (formerly smartrickpicks/kiwi-semantic-control), branch: main
Open PRs: none known

## Task Backlog

### [TODO]
- **Choose ingestion attribution pattern** — Pattern A (per-user folders) vs Pattern B (manifest file). Owner: Architect. Evidence source: docs/ingestion/INGESTION_DOCTRINE.md. Requires operator workflow feedback before deciding.
- **Define auth integration for submitter identity** — V2 scope. Owner: Architect. Evidence source: V2 scope document (not yet created). Blocked until V2 scope is confirmed.
- **Specify Drive/Dropbox/Email Drop integration requirements** — V2 scope. Owner: Architect. Evidence source: V2 scope document. Currently documented as stubs only.

### [IN_PROGRESS]
- (none)

### [BLOCKED]
- (none)

### [DONE]
- **Lock gate_parse owning view to data_source_panel** — Confirmed: docs/ui/gate_view_mapping.md:11 already maps `gate_parse` → `data_source_panel`
- **Align Human-Agent-Workflow-V1.json node labels with canonical terms** — Confirmed: spec uses `data_source` (line 30), `single_row_review` (line 44), `submit_patch_request` (line 82), with legacy labels preserved in rename mappings (lines 176-181)
- **Product naming normalization** — "Orchestrate OS" canonical across edited docs; legacy "Kiwi Semantic Control Board" uses parenthetical. Commit: 3dae309
- **Terminology normalization** — Verifier, Record Inspection, Submit Patch Request standardized across 6 files. Commit: 0205089

## Definition of Done
- Linked evidence (commit/PR/docline)
- Terminology compliance check passed (no forbidden user-facing labels)
- Unresolved items must have named owner + required evidence source
