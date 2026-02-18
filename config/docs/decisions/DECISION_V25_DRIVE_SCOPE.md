# Decision: V2.5 Google Drive Integration Scope

**Version:** 2.5
**Date:** 2026-02-13
**Status:** Locked

## Decision

Google Drive integration operates in **two-way mode** (pull + export push) with **manual refresh**, a **working copy model**, and **status-based export naming**. Imports always create a local working copy; the source file in Drive is never modified. Exports produce distinctly named files (`_InProgress` or `_Final`) written to a user-selected Drive folder.

## Context

Orchestrate OS users store contract workbooks (`.xlsx`, `.csv`) in shared Google Drive folders as part of their existing workflow. Currently, importing a file into the governance pipeline requires downloading from Drive, then uploading via the browser. Exporting governed artifacts requires downloading from the UI, then manually uploading back to Drive. This friction slows adoption and creates version confusion.

The system already has Google OAuth for login (`server/routes/auth_google.py`), JWT sessions (`server/jwt_utils.py`), PostgreSQL persistence (`server/db.py`), RBAC middleware (`server/auth.py`), and audit logging (`server/audit.py`). Adding Drive as a first-class data source leverages the existing Google ecosystem integration and eliminates the manual download/upload cycle.

Drive integration follows the same gated workflow as the V2.5 API initiative: DOCS → CLARITY → ALIGNMENT → CODE → AUDIT.

## Locked Product Decisions

### LPD-1: Integration mode — two-way (pull + export push), controlled scope

Users can **pull** files from Drive into the governance pipeline and **push** governed exports back to Drive. The integration does not provide full two-way sync — it is controlled, user-initiated, and directional. Pull creates a working copy; push creates a new file (never overwrites the source).

### LPD-2: Refresh model — manual refresh only

There is no auto-refresh, polling, or webhook-driven sync. Users explicitly click "Refresh from Drive" to re-import the latest version of a source file. This preserves governance integrity by ensuring state changes are deliberate and auditable.

### LPD-3: Import behavior — always create working copy; never overwrite source

Importing a file from Drive creates a **new working copy** in the governance pipeline. The original Drive file is never modified, moved, or deleted. If the user imports the same file again, a new version of the working copy is created. The previous version remains accessible.

### LPD-4: Export behavior — status-based naming

Users choose between two export actions:
- **"Save In Progress"** — exports the current governed state as `{filename}_InProgress_{timestamp}.xlsx` to the selected Drive folder
- **"Export Final"** — exports the finalized governed state as `{filename}_Final_{timestamp}.xlsx` to the selected Drive folder

Both actions create new files in Drive; neither overwrites existing files.

### LPD-5: Existing red-cell input files accepted

The import pipeline accepts workbooks with existing red-cell annotations (flagged cells from prior manual review). These are preserved as-is during import. The system does not require files to be "clean" before import.

### LPD-6: Patch backfill from external red cells is out-of-scope

If an imported file contains red cells from external review, the system does not attempt to reverse-engineer patch requests from those annotations. Red cells are visual metadata only; governance state is tracked through the patch lifecycle.

### LPD-7: Workbook cell style/colors must survive export round-trip

Governed workbooks use cell colors (red, green, yellow) as visual indicators of governance status. Export must preserve these styles with acceptable fidelity. If the SheetJS community edition cannot preserve full style parity, a server-side library (`openpyxl`) or SheetJS Pro will be evaluated.

## Non-Negotiables

### NN-1: Keep `/api/v2.5/` canonical

All Drive integration endpoints live under the existing `/api/v2.5/` namespace. No separate API version or namespace for Drive operations. Drive endpoints follow the same resource-style conventions as all other V2.5 endpoints.

### NN-2: Do not weaken production RBAC/governance

Drive integration must not bypass, weaken, or create shortcuts around existing role-based access control. Import and export operations are subject to the same permission checks as any other data mutation. An Analyst cannot export a file that requires Admin approval.

### NN-3: Sandbox role simulation rules unchanged

The sandbox/simulation mode used for role demonstration and testing is not affected by Drive integration. Drive operations are available only in production mode with authenticated users.

### NN-4: All Drive actions must be auditable

Every Drive operation (connect, disconnect, import, export, refresh, error) emits a structured audit event to the `audit_events` table via `server/audit.py`. Audit events include: actor, role, timestamp, Drive file ID, operation type, and outcome (success/failure).

### NN-5: Secrets in environment only; never in repo

Google OAuth credentials (`GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`), encryption keys for stored refresh tokens, and any other sensitive configuration remain in environment variables. No secrets are committed to the repository, stored in configuration files, or logged.

### NN-6: No mixed response envelope shapes

Drive API responses follow the same envelope shape as all other V2.5 endpoints. Success responses use `{ data: ... }`. Error responses use `{ error: { code, message, details } }`. No special envelope for Drive operations.

## Explicit Out-of-Scope

| Item | Reason |
|------|--------|
| Auto-refresh / polling | Risk of overwriting governed state; manual control preserves audit integrity |
| Patch backfill from external red cells | Reverse-engineering patches from visual annotations is unreliable and breaks governance provenance |
| Multi-file batch import | Complexity not justified for v1; users import files individually to maintain clear provenance |
| Google Sheets native editing | Governance requires a snapshot model; live editing in Sheets would bypass the patch lifecycle |
| Drive webhook / push notifications | Adds infrastructure complexity (public webhook endpoint, verification, subscription management) without clear benefit given manual-refresh model |
| Conflict resolution between Drive and local versions | Working copy model eliminates conflicts by design — local copy is independent of Drive source |
| Per-workspace Drive folder mapping configuration | Admin-configured default folders per workspace adds UX complexity; users select folders per-operation in v1 |

## Alternatives Considered

| Option | Rejected Because |
|--------|-----------------|
| Dropbox integration | Users are in the Google ecosystem (Google login, Google Drive for file storage). Dropbox would require a separate OAuth flow and has lower adoption among target users |
| Direct Google Sheets editing | Governance requires a snapshot model where changes go through the patch lifecycle (Draft → Submitted → Approved → Applied). Live editing in Sheets would bypass this entirely and break audit integrity |
| Auto-sync (real-time or scheduled) | Risk of overwriting governed state without user awareness. Manual control ensures every import/export is a deliberate, auditable action. Auto-sync also introduces conflict resolution complexity |
| Read-only mode (import only) | Users need to export governed artifacts back to Drive for distribution and sign-off. Import-only mode would force manual download/upload for exports, defeating the purpose of the integration |
| Full two-way sync with conflict resolution | Dramatically increases complexity (conflict detection, merge strategies, UI for resolution). Working copy model is simpler, safer, and sufficient for governance workflows |

## Cross-References

- `docs/handoff/V25_DRIVE_READINESS_REPORT.md` — Drive integration readiness audit
- `docs/handoff/V25_READINESS_REPORT.md` — V2.5 core readiness audit
- `docs/decisions/DECISION_V25_DB.md` — PostgreSQL canonical database decision
- `docs/decisions/DECISION_STORAGE_POLICY.md` — V2.3 storage policy
- `docs/features/V25_GOOGLE_DRIVE_INTEGRATION.md` — Feature specification
- `docs/api/API_SPEC_V2_5_CANONICAL.md` — API contract
- `server/routes/auth_google.py` — Existing Google OAuth implementation
- `server/audit.py` — Audit event emission
- `server/auth.py` — RBAC middleware
