# View: Promotion

> Final stage for promoting Approved Patches to Baseline Patches and exporting PR-ready artifacts.

## Entry Conditions

| Condition | Required |
|-----------|----------|
| Patch in Admin_Approved or Applied state | Yes |
| User authenticated | Yes |
| Minimum role | Admin |
| gate_admin passed | Yes |
| Smoke (Strict) passing | Yes |

## Visible Artifacts

| Artifact | Description | Required |
|----------|-------------|----------|
| Patch Summary | Intent, evidence, decisions | Yes |
| Current Baseline Version | config_pack.base.json version | Yes |
| New Baseline Version | Proposed version after apply | Yes |
| Changelog Entry | Full changelog text | Yes |
| Smoke (Strict) Evidence | Current pass status with SHA256 | Yes |
| Export Preview | Patch file contents | Yes |
| Audit Trail | Full decision history | Yes |

## Allowed Actions by Role

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| View promotion artifacts | No | No | Yes |
| Promote Patch to Baseline | No | No | Yes |
| Export to PR | No | No | Yes |
| Download patch file | No | No | Yes |
| Copy changelog entry | No | No | Yes |

## Disallowed Actions

| Action | Reason |
|--------|--------|
| Edit patch content | Locked after admin approval |
| Promote without Smoke (Strict) pass | Baseline mutation requires evidence |
| Skip changelog | Changelog is required artifact |
| Revert promotion | Use git revert instead |

## Two-Stage Process

### Stage 11: Promote Patch to Baseline

| Step | Description |
|------|-------------|
| 1 | Verify Smoke (Strict) is currently passing |
| 2 | Confirm baseline version increment |
| 3 | Click "Promote Patch to Baseline" |
| 4 | System-derived: baseline version updated in memory |
| 5 | Audit log records promotion timestamp |

### Stage 12: Export to PR

| Step | Description |
|------|-------------|
| 1 | Review export preview |
| 2 | Confirm changelog entry |
| 3 | Click "Export to PR" |
| 4 | System-derived: patch file generated |
| 5 | Audit log records export path |

## Audit/Evidence Requirements

| Event | Logged | Evidence |
|-------|--------|----------|
| Promote Patch to Baseline | Yes | timestamp, patch_id, admin_actor, old_version, new_version |
| Export to PR | Yes | timestamp, patch_id, admin_actor, export_path, sha256 |

## State Transitions

| From State | To State | Action | Role |
|------------|----------|--------|------|
| Admin_Approved | Applied | Promote Patch to Baseline | Admin |
| Applied | Promoted | Export to PR | Admin |

## Export Artifacts

| Artifact | Format | Destination |
|----------|--------|-------------|
| Patch file | JSON | config/config_pack.patch.json |
| Changelog entry | Markdown | CHANGELOG.md |
| Smoke (Strict) evidence | Text | docs/replit_baseline.md |

## Related Documents

- [gate_view_mapping.md](../gate_view_mapping.md) — Gate ownership
- [admin.md](../roles/admin.md) — Admin role permissions
- [admin_approval_view.md](admin_approval_view.md) — Previous stage
- [Flow-Doctrine.md](../../V1/Flow-Doctrine.md) — Workflow stages 11-12
