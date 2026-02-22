# V3 Parity and Cutover Checklist

## Branch + Baseline
- [ ] Working branch is correct for V3 task.
- [ ] `git status` reviewed (no accidental unrelated staging).
- [ ] No merge markers in `ui/viewer/index.html`.

## Build + Smoke
- [ ] `bash scripts/replit_smoke.sh --allow-diff` passes.
- [ ] PTL opens/runs (upload + URL) without spinner hang.
- [ ] Record Inspector V2 route opens under feature flag.

## PTL -> Workspace Flow
- [ ] PTL `Edit` opens full workspace route (not modal-only edit).
- [ ] Scope/check context is preserved (highlighted target).
- [ ] Evidence panel shows relevant annotation/PDF context.
- [ ] Green manual attestation required before proceed/submit.
- [ ] False-positive highlight can be unmapped with audit record.
- [ ] Non-highlighted text can be selected to create alias term with immediate doc-level mapping effect.

## Editing and Evidence
- [ ] Any mutation requires reason/evidence capture.
- [ ] Status/value edits produce audit events.
- [ ] Patch payload still includes `preflight_context`.

## Generation Composer
- [ ] Clause payload inclusion/removal works in canonical order.
- [ ] Live preview updates reflect clause payload choices.
- [ ] Generation mutations are permission-gated separately from ingestion mutations.

## New Counterparty Flow
- [ ] Counterparty selector includes `Create New`.
- [ ] Required legal entity/account/address/contact fields enforced.
- [ ] Suggested extracted name prefill works when available.
- [ ] Invalid address/account state blocks submit.

## Roles/Permissions
- [ ] Analyst edit + submit works.
- [ ] Verifier review path works.
- [ ] Admin full controls work.
- [ ] Contract Author (test perms) obeys configured permission matrix.
- [ ] Domain split is enforced: ingestion-authoring perms vs generation-authoring perms.

## Legacy Fallback
- [ ] Legacy Review/Evidence views still reachable behind fallback.
- [ ] No blocker regressions in existing verifier/admin flows.

## Cutover Gate
- [ ] V3 parity checks pass.
- [ ] Reviewer sign-off captured.
- [ ] Replit staging smoke + happy-path rerun pass.
- [ ] GO/NO-GO explicitly recorded.
