# Spec: PTL Edit -> Record Inspector V2 Flow

## Purpose
Define the runtime behavior and payload contract when PTL drives users into `Record Inspector V2 (Beta)` for targeted correction/review.

## Entry Trigger
From PTL section rows (`Opportunity Spine`, `Schedule Structure`, `Financials Readiness`, `V2 Add-ons Readiness`), user clicks `Edit`.

## Navigation Contract
Route to workspace with context payload:
- route: `#/record-inspector-v2`
- required query/state context:
  - `record_key`
  - `doc_id` (if available)
  - `scope` (module key)
  - `check_code`
  - `check_label`
  - `base_status`
  - `effective_status`
  - `base_value`
  - `effective_value`
  - `gate_color`
  - `health_score`

## Workspace Behavior
- Open full-page workspace.
- Jump to targeted section and visually highlight target check/field group.
- Show evidence panel (annotation/PDF context) for targeted check.
- Show change modal on mutation:
  - required reason/evidence text,
  - link to source evidence location where possible.

## Mapping and Alias Operations (Ingestion Side)
- User can unmap a highlighted extraction when it is false-positive/duplicate.
- User can select non-highlighted raw PDF text and create an alias term.
- Alias creation immediately applies to current document mapping context.
- Alias rule application is document-scoped in V3 (global promotion can remain verifier/admin-governed).

## Generation Composer Operations (Creation Side)
- Workspace provides payload-driven clause assembly in canonical order.
- User can add/remove clause payloads (for example sync rights variants) and see live preview updates.
- Canonical ordering is enforced by rule engine; user controls inclusion and payload values, not arbitrary ordering.
- Generated output remains draft until existing patch/approval flow marks it approved.

## PTL Green Manual Review Rule
- Even if gate is green, user must manually attest review before proceed/submit:
  - checkbox: `I reviewed all sections`
  - submit actions disabled until checked.

## New Counterparty (Create New) Requirements
- In counterparty selector, include `Create New` option.
- If chosen, display required creation block:
  - legal entity binding,
  - counterparty legal/account name,
  - billing address fields,
  - required contact minimum set.
- Prefill suggested counterparty name from extraction hints when available.
- Validate address format/requiredness before allowing submit.

## Permission Rules (V3)
- Analyst:
  - can perform ingestion-side edits in workspace, can submit patches.
- Verifier:
  - can review/edit verifier-allowed fields, approve/reject via existing flow.
- Admin:
  - full permissions.
- Contract Author (test perms):
  - generation-side scoped permissions via permission matrix.

## Permission Domain Split (Must Enforce)
- Ingestion domain: extraction mapping, unmap/remap, alias creation, preflight correction.
- Generation domain: payload/clause composition, template-based draft assembly.
- Role permissions must be assignable per domain to prevent accidental cross-authority edits.

## Required Audit Events
- `PTL_EDIT_OPENED`
- `WORKSPACE_SECTION_FOCUSED`
- `FIELD_EDIT_PROPOSED`
- `STATUS_OVERRIDE_APPLIED`
- `VALUE_OVERRIDE_APPLIED`
- `EVIDENCE_NOTE_CAPTURED`
- `NEW_COUNTERPARTY_CREATED`
- `UNMAP_APPLIED`
- `ALIAS_CREATED`
- `ALIAS_RULE_APPLIED_DOC`
- `CLAUSE_PAYLOAD_ADDED`
- `CLAUSE_PAYLOAD_REMOVED`
- `GENERATION_DRAFT_UPDATED`
- `PATCH_DRAFT_CREATED`
- `PATCH_SUBMITTED`

Each event requires:
- `at_utc`, `actor`, `role`, `record_id|record_key`, `scope`, `check_code`, `details`.

## Acceptance Criteria
- PTL `Edit` consistently opens workspace with correct context.
- User can complete correction path without returning to legacy screens.
- Patch payload contains preflight context and evidence comments.
- Permission and audit logs enforce/reflect all mutation actions.
- False-positive highlights can be unmapped and audited.
- Non-highlighted text alias creation works and immediately remaps document context.
- Generation composer supports payload add/remove with canonical ordering and live preview.
