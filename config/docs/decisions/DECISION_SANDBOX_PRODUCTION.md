# Decision Memo: Sandbox vs Production Split

**Version:** 2.3  
**Status:** Locked

## Sandbox Mode (formerly "Demo" / "Playground")

- **Permissionless**: All users can access all features without authentication
- **No Admin role**: Admin role is disabled in Sandbox to prevent accidental governance actions
- **Guided Next progression**: Users follow the standard workflow (upload → triage → review)
- **Queues and lifecycle visible**: All triage queues and lifecycle stages are accessible
- **Local storage only**: All changes stored in browser, no server persistence

## Production Mode

- **Strict authentication**: Google OAuth required (when configured)
- **Role-based access control**: Analyst, Verifier, Admin with enforced permissions
- **Admin role available**: Full governance capabilities
- **Permission matrix enforced**: Actions gated by role (see `_governedDecisions.canPerformAction`)

## Switching

Toggle is available in Admin → Environment Mode panel. Switching from Sandbox to Production requires re-authentication if OAuth is configured.
