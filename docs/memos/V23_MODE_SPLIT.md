# V2.3 Mode Split — Sandbox vs Production (Locked)

## Overview

V2.3 introduces a strict split between Sandbox and Production modes. The split governs which actions require role-based permission gates and which are permissionless.

## Sandbox Mode (formerly "Playground")

- Permissionless: all governance actions are allowed regardless of role.
- No Admin role enforcement — any user can perform admin-level actions.
- Intended for training, experimentation, and offline review without governance friction.
- `_governedDecisions.canPerformAction(action, role, false)` always returns `true`.

## Production Mode

- Strict role gates enforced via `_governedDecisions.canPerformAction(action, role, true)`.
- Uses email-based access control with Google sign-in for OAuth.

### Permission Matrix (Production)

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| edit_draft | Yes | — | Yes |
| submit_patch | Yes | — | Yes |
| verify_patch | — | Yes | Yes |
| approve_patch | — | — | Yes |
| promote_rule | — | — | Yes |
| attach_schedule | Yes | — | Yes |
| set_governing | Yes | — | Yes |
| rollback | — | — | Yes |

### Governed Decision Points (Wired)

The following actions check `_governedDecisions.canPerformAction()`:
1. `submitPatchRequest` — blocks non-analyst/admin in production
2. `verifierApprove` — blocks non-verifier/admin in production
3. `adminApprove` — blocks non-admin in production
4. `createPatchRollback` — blocks non-admin in production

### Self-Approval Block

In both modes, the patch author cannot approve their own patch at Verifier or Admin stage. This is enforced separately from the mode split.

## Mode Detection

- Production mode is activated when Google OAuth is configured and a valid session exists.
- Sandbox mode is the default when OAuth is not configured.
- Mode is displayed in the sidebar as `Mode: Analyst` (sandbox) or `Mode: {Role}` (production).

## Cross-References

- `docs/decisions/DECISION_SANDBOX_PRODUCTION.md` — full decision record
- `docs/ui/ui_principles.md` — role-gating UI principles
