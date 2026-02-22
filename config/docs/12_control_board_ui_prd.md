# 12 — Control Board UI PRD (Governance‑Only, Offline‑First)

## 1) Problem / Why this UI exists
- This UI is a governance surface for the semantic control plane. It allows operators to author, validate, preview, and export semantic rules as files.
- It is not a runtime console. It does not execute pipelines, call external APIs, or manage credentials.
- It standardizes deterministic, artifact‑driven workflows so that semantics remain explicit, auditable, and reproducible.

Success criteria
- Operators can complete the Discover→Draft→Validate→Preview→Export→PR/Review→Version loop using only local artifacts.
- Deterministic preview (smoke) is the arbiter of correctness; UI never treats editor/LSP diagnostics as authoritative.

---

## 2) Personas
- Operator
  - Can: discover issues, draft rules (intent + mapping), run validation/preview locally, prepare/export patches, update expected outputs when intentional, assemble PR packages.
  - Cannot: run DataDash, call Salesforce or other APIs, store credentials, edit base without process.
- Verifier
  - Can: review diffs, validation reports, preview evidence, ensure checklist compliance, approve version bumps.
  - Cannot: bypass smoke gate, merge changes without artifacts.
- Analyst
  - Can: propose rule intent (WHEN/THEN/BECAUSE), map to patch schema, provide example scenarios.
  - Cannot: modify determinism settings or introduce runtime connectors.

---

## 3) Information Architecture (aligned with 08_control_board_ui_spec)
Left‑Nav Sections and Tabs
1) Overview
   - Welcome, Scope & Truth, Changelog
2) Authoring
   - Rule Drafts, Patch Builder, Templates
3) Validation
   - Shape Validator, Conflict Checker, Determinism Rules
4) Preview
   - Baseline Preview, Edge‑Case Preview, Diff Pane
5) Export
   - Patch Export, PR Summary, Governance Checklist
6) Evidence
   - Smoke Logs, Baselines, Expected Outputs
7) Settings (Local‑Only)
   - Paths, Sorting Rules, Conventions

DataDash ergonomics
- All Data Grid (sortable tables), issue drilldown, diff panes, rule editor with side‑by‑side intent→schema mapping.

---

## 4) Core Flows with Acceptance Criteria
Flow: Discover → Draft → Validate → Preview → Export Patch → PR/Review → Version

4.1 Discover
- Behavior: List current examples, expected outputs, recent changes; overview tables of preview issues (if any) from last run.
- AC
  - Table supports sort by severity (blocking > warning > info), subtype, join triplet; stable ordering.
  - Links to relevant artifacts open locally (no network calls).

4.2 Draft
- Behavior: Author rule intent (WHEN/THEN/BECAUSE) and map to patch schema fields (rule_id, when, then, severity).
- AC
  - Rule Draft object stored locally (UI draft JSON), not auto‑applied to config.
  - Mapping UI prevents invalid operators/actions and enforces canonical sheet/field names.
  - Draft can be added to a Patch Draft (not yet exported).

4.3 Validate
- Behavior: Run offline validator to produce a validation report (shape + conflicts + base_version guard).
- AC
  - Shows status ok/error, missing sections, conflict descriptions, and counts.
  - No external calls; validator output is rendered verbatim with friendly formatting.
  - Failing base_version mismatch blocks export.

4.4 Preview
- Behavior: Run harness via shell to produce sf_packet.preview.json for baseline or edge‑case dataset; show diff vs expected.
- AC
  - Baseline and edge‑case modes available; default is baseline.
  - Diff pane uses normalized JSON (sorted keys); array ordering is stable and deterministic.
  - UI indicates "pass" only if strict smoke reports no diff; otherwise shows unified diff and remediation hints.

4.5 Export Patch
- Behavior: Convert Patch Draft → config_pack.<version>.patch.json (changes[]), write to config/ after explicit confirmation.
- AC
  - File write requires operator confirmation; path shown before save.
  - No changes applied to base; only a new patch file is created.
  - Optionally produce a PR summary markdown with WHY, affected files, and smoke status.

4.6 PR/Review
- Behavior: Present governance checklist (REVIEW_CHECKLIST.md), smoke evidence, and CHANGELOG template.
- AC
  - Verifier can verify strict smoke pass and validation report.
  - UI blocks "ready for review" status if smoke failed or validation blocked.

4.7 Version
- Behavior: Guide version bump and CHANGELOG updates; operator must confirm writes.
- AC
  - Version bump recorded only on explicit confirmation; UI never edits files silently.
  - CHANGELOG entry includes WHY and smoke evidence references.

---

## 5) Artifact I/O Map (files only)
Reads
- config/config_pack.base.json
- config/*.patch.json (including new Patch Draft target)
- examples/standardized_dataset.*.json, examples/expected_outputs/*.json
- out/sf_packet.preview.json, validator stdout/stderr captured locally
- CHANGELOG.md

Writes (explicit confirmations required)
- config/config_pack.<version>.patch.json (new patch)
- examples/expected_outputs/*.json (only when operator chooses to update expected)
- CHANGELOG.md (append entries; template + confirm)
- Optional: docs/replit_baseline.md (append environment/hash notes)

All writes are local file operations. No network usage.

---

## 6) Determinism Requirements
- Sorting rules
  - Contract rows: join triplet (contract_key asc, file_url asc, file_name asc; nulls last)
  - Issues/actions/change log: (contract_key, file_url, file_name, sheet, field, type)
  - Severity chips: blocking > warning > info
- Smoke is the arbiter
  - Baseline smoke must pass before a patch is considered reviewable.
  - Edge‑case smoke required if join/fallback is affected.
- UI diagnostics are non‑authoritative; they must reflect harness outputs.

---

## 7) Non‑Goals / Out‑of‑Scope
- No runtime execution or external connectors (Salesforce, S3, etc.)
- No credentials or secret handling
- No LLM prompts or model behavior definition
- No API integrations; artifact‑based I/O only
- No production parity claims (governance preview only)

---

## 8) MVP vs vNext
MVP (read‑only viewer + runner)
- Read and render sf_packet.preview.json and validation report
- Run validation and preview via shell commands
- Show diffs vs expected outputs (normalized JSON)
- Acceptance (MVP)
  - Can load baseline/edge datasets and produce pass/fail clearly
  - Can open related artifacts (base, patch, expected outputs) locally
  - No write operations without explicit confirmation dialogs

vNext (draft builder + export helper)
- Rule Draft editor (intent + mapping), Patch Draft builder
- Patch export to config/; PR summary generator
- Governance checklist integration; version bump helper
- Acceptance (vNext)
  - Patch export creates valid patch file with changes[]
  - Strict smoke can be run from the UI wrapper and its outcome is displayed

---

## 9) Open Questions (≤10)
1) Should the UI provide a guided wizard for rule_id naming to reduce collisions?
2) What minimal lint rules should apply to descriptions (e.g., require WHY sentence)?
3) Should expected outputs update flow require dual confirmation (author + verifier) before write?
4) How should the UI display multiple patch drafts targeting the same base (folder vs labeled table)?
5) Is a dry‑run mode for patch export useful (write to temp path first)?
6) Do we need a batch preview mode to compare multiple datasets in one session?
7) Should the UI surface a simple hash (SHA256) for preview outputs to simplify audits?
8) How much of the smoke script log should be stored as evidence in the repo (size vs audit need)?
9) Is a minimal redaction step needed for local logs before attaching to PR summaries?
10) Should the UI enforce a default version bump strategy (patch/minor) based on rule impact categories?

