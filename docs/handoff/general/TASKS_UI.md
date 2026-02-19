# TASKS_UI (Handoff — UI Backlog)

Audience: Governance verifiers and UI operators
Purpose: Track UI tasks with governance constraints and evidence links
Scope: UI copy and contracts only; no runtime or implementation claims
Non-Goals: No claims of completion without evidence (commit/PR URL)
Authority Level: Informational; defers to canonical docs
Owner Agent: Documentation architect (Orchestrate OS)
Update Rules: Each task must include scope, files likely to touch, and acceptance tests; unresolved items must name owner and required evidence source

Repository: Orchestrate OS (formerly smartrickpicks/kiwi-semantic-control), branch: main
Open PRs: none known

## Backlog

### Record Inspection: Field Order & Guard Modal (docs-only)
- Scope: Ensure Field Cards/Groups/Filters/Proposed Change/mini prompt/guard modal copy present in Record Inspection doc
- Files likely to touch: docs/ui/views/single_row_review_view.md
- Status: **Open** — Owner: Documentation architect. Current SRR doc (433 lines, v2.2) does not contain Field Cards, Field Groups, or guard modal sections. Evidence source: requires authoring these sections from UI implementation in ui/viewer/index.html
- Acceptance: sections added; no runtime claims

### Data Source: Rotation/Disconnect copy parity
- Scope: Mirror rotation (Active→Saved) and Disconnect guidance in viewer copy
- Files likely to touch: docs/ui/views/data_source_view.md; ui/viewer/index.html
- Status: **Open** — Owner: Documentation architect. Current data_source_view.md does not contain Rotation or Disconnect copy. Evidence source: requires documenting from ui/viewer/index.html behavior
- Acceptance: copy present and consistent

### Spec/Mapping Canonicalization
- Status: **Done**
- Evidence: docs/specs/Human-Agent-Workflow-V1.json uses canonical node IDs — `data_source` (line 30), `single_row_review` (line 44), `submit_patch_request` (line 82). Gate mapping confirmed: `gate_parse` → `data_source_panel` (docs/ui/gate_view_mapping.md:11). Legacy labels preserved in rename mappings (lines 176-181).

### Record Inspection: Evidence Pack + Patch Editor Refinement (v1.4.19)
- Scope: Refine Evidence Pack to reduce analyst load; make patch semantics deterministic and patch-type driven
- Files likely to touch: ui/viewer/index.html; docs/ui/views/single_row_review_view.md
- Acceptance tests:
  - Old/New values visually distinct (Old locked subdued; New prominent editable)
  - Observation/Expected are dropdown-only (no text areas)
  - Patch Type selector changes visible form sections
  - Repro controls appear only when required
  - Override badge appears and suppresses repro requirement
  - Docs updated to match UI
- Status: **Open** — Owner: Documentation architect. Evidence source: requires verification against ui/viewer/index.html implementation and SRR doc update

### Record Inspection: Mini-Queue + Auto Patch Type Semantics (v1.4.20 — docs-only)
- Scope: Document Field Inspector as mini-queue with field states and auto Patch Type behavior
- Files likely to touch: docs/ui/views/single_row_review_view.md
- Acceptance tests:
  - Record Inspection doc includes mini-queue field states (TODO, VERIFIED, RFI, PATCHED)
  - Record Inspection doc includes field actions (Verify, Blacklist Flag, RFI, Patch)
  - Record Inspection doc includes auto Patch Type behavior (read-only, action-driven)
  - Record Inspection doc includes Blacklist category dropdown + subject derivation
  - Record Inspection doc includes RFI behavior (Justification = question)
  - Record Inspection doc includes guard modal for unresolved PATCHED/RFI fields
  - No UI code files modified
- Status: **Open** — Owner: Documentation architect. SRR doc (v2.2) does not yet contain these sections. Evidence source: requires authoring from UI implementation

### Record Inspection: Field Inspector Mini-Queue UI Implementation (v1.4.20)
- Scope: Implement Field Inspector mini-queue behavior with field states, actions, filters, and guard modal
- Files likely to touch: ui/viewer/index.html
- Acceptance tests:
  - AT-01: Verify action sets VERIFIED and removes field from TODO list
  - AT-02: Blacklist action sets PATCHED + auto Patch Type = Blacklist Flag, without editing value
  - AT-03: RFI action sets RFI + auto Patch Type = RFI
  - AT-04: Editing a field sets PATCHED + auto Patch Type = Correction
  - AT-05: Filter chips reflect correct counts (TODO/Verified/RFI/Patched/All)
  - AT-06: Guard modal appears when leaving Record Inspection with unresolved PATCHED/RFI fields
  - AT-07: Patch Type is not user-editable (read-only display)
- Status: **Open** — Owner: UI developer. No mini-queue, guard modal, or Field Inspector references found in current ui/viewer/index.html. Evidence source: requires implementation
