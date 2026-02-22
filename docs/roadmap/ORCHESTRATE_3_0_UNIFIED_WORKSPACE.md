# Orchestrate 3.0: Unified Contract Workspace Roadmap

## Objective
Ship a single contract operations surface centered on `Record Inspector V2 (Beta)` that unifies:
- preflight ingestion and gate actions,
- targeted edits with evidence context,
- patch/RFI/audit submission flow.

The immediate priority is ingestion -> modification -> creation inside one workflow, with permissions and custody correctness preserved.

## Locked Decisions (From Product Clarity Session)
- Working name: `Record Inspector V2 (Beta)`.
- PTL remains gate entrypoint (`green`, `yellow`, `red`), but edits route to workspace.
- PTL `Edit` opens full workspace route (not in-place modal).
- Any change requires reason/evidence capture modal.
- `Green` still requires manual review attestation before proceed/submit.
- In ingestion context, users can unmap false-positive highlights and create aliases from non-highlighted text.
- Alias rules apply immediately to the current document context.
- In generation context, users compose clause payloads in canonical order with live preview updates.
- Existing patch submission pipeline remains source of truth.
- New counterparty path is required in V3:
  - Counterparty selector supports `Create New`.
  - Bind to legal entity.
  - Capture account/contact/billing fields for first-time record creation.
  - Prefill suggested name when detected.
- Role model for V3:
  - `Analyst`, `Verifier`, `Admin`, `Contract Author (test perms)`.
- Permission model is domain-split:
  - ingestion-side authoring permissions,
  - generation-side authoring permissions.
- Legacy Review/Evidence views stay as fallback until parity and stability gates pass.

## V3 Scope (Must Ship)
- PTL deep-link into workspace with section/check context.
- Workspace focused edit mode with section highlight and evidence/PDF context.
- Change-reason modal for overrides and edits.
- Unmap + alias interactions for ingestion correction.
- Canonical payload clause composer for generation.
- Manual green attestation control in PTL flow.
- New counterparty create flow + required validations.
- Permission enforcement and audit event coverage for all write actions.

## Out of Scope for Initial V3 (Planned V3.1+)
- Full Airlock cross-domain orchestration.
- Broad enterprise search/index (Elastic/Meli) across all tools.
- Complete corrupt-document assisted reconstruction pipeline automation.
- Final legacy view deprecation/removal.

## Phase Plan (Dependency Order)
1. Phase 0: Spec lock and governance
2. Phase 1: PTL -> workspace routing and context payload
3. Phase 2: Focused editor + evidence-linked PDF workflow
4. Phase 3: Ingestion mapping controls (`unmap`, `alias`, immediate doc apply)
5. Phase 4: Generation clause composer (payload inclusion, canonical order, live preview)
6. Phase 5: New counterparty creation path
7. Phase 6: Role/permission matrix expansion (`Contract Author`, domain split)
8. Phase 7: Parity validation, staged cutover, fallback plan

## Dependencies and Risks
- Dependency: stable PTL + patch payload context path.
- Dependency: reliable annotation anchors for section/check targeting.
- Dependency: deterministic canonical clause-ordering rules.
- Risk: route changes could break existing reviewer flows.
- Risk: new customer creation can produce partial/invalid CRM records.
- Risk: ingestion edits and generation edits crossing role boundaries.
- Mitigation: feature flag V2 route, strict validation gates, parity checklist before default-on.

## Definition of Done for V3
- Analyst can run PTL, attest review, open workspace, edit with evidence, and submit patch.
- Verifier can open same workspace context and validate edits with annotation visibility.
- Admin path remains functional for approvals/escalation.
- New counterparty path is complete and audited.
- Unmap/alias and generation composer actions are audited and permission-gated.
- Replit smoke + runtime parity checklist pass with no blocker findings.
