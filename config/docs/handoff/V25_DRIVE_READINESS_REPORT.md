# V2.5 Drive Integration Readiness Report

**Version:** 0.1 (Gate 1 Draft)
**Date:** 2026-02-13
**Status:** Pending Alignment Approval

---

## 1. Executive Summary

Orchestrate OS is adding Google Drive as a first-class data source for the governance UI. Users store contract workbooks (`.xlsx`, `.csv`) in shared Google Drive folders and need to import them into the governance pipeline for triage, patching, and review — then export governed artifacts back to Drive.

The integration operates in **two-way mode** (pull + export push) with **manual refresh only** and a **working copy model**: imports always create a local working copy; the source file in Drive is never overwritten. Exports produce status-named files (`_InProgress` or `_Final`) written back to a user-selected Drive folder.

The existing Google OAuth infrastructure (used for login) provides the foundation. Drive scopes must be added to the existing OAuth consent screen, and a Drive API client library must be installed server-side. The file import pipeline (`parseUnifiedWorkbook`) already handles `.xlsx`/`.csv` parsing. The primary gaps are: Drive API client library, file picker UI, token refresh persistence for long-lived Drive access, and provenance metadata tracking.

This report audits the current repo against Drive integration requirements and identifies what exists, what is partial, and what is missing.

---

## 2. Readiness Matrix

| # | Area | Status | Risk | Notes |
|---|------|--------|------|-------|
| DR1 | Google OAuth infrastructure | **Done** | Low | `server/routes/auth_google.py` implements Google OAuth (OIDC) login flow. OAuth client ID and secret already configured. Only needs Drive scopes (`drive.readonly`, `drive.file`) added to the existing consent screen and token request |
| DR2 | Token storage & refresh persistence | **Partial** | High | Login tokens are stored server-side for session validation, but no `refresh_token` persistence exists for long-lived Drive access. Drive API requires offline access (`access_type=offline`) to mint refresh tokens. Needs a `drive_connections` table with encrypted refresh token storage |
| DR3 | Drive API client library | **Missing** | Medium | `google-api-python-client`, `google-auth-httplib2`, and `google-auth-oauthlib` are not in `requirements.txt`. Must be installed before any Drive API calls can be made |
| DR4 | File import pipeline | **Done** | Low | `parseUnifiedWorkbook` in `ui/viewer/index.html` already handles `.xlsx` and `.csv` parsing via SheetJS. Server-side ingest can receive file bytes from Drive API and pass them through the same pipeline |
| DR5 | Export pipeline | **Partial** | Medium | SheetJS export exists in the UI for generating `.xlsx` downloads. No server-side Drive upload capability. Needs `files().create()` / `files().update()` calls via Drive API with proper MIME type handling |
| DR6 | Audit event infrastructure | **Done** | Low | `server/audit.py` emits structured audit events to PostgreSQL `audit_events` table. Only needs new event type constants: `drive.connect`, `drive.disconnect`, `drive.import`, `drive.export`, `drive.refresh` |
| DR7 | RBAC middleware | **Done** | Low | `server/auth.py` has role-based access control with Analyst/Verifier/Admin role checks. Needs Drive-specific permission rules: Analyst can import/export own files; Admin can manage Drive connections; Verifier has read-only Drive provenance access |
| DR8 | Drive file browser UI | **Missing** | Medium | No file picker component exists. Needs a Drive folder browser with file selection, preview metadata, and import trigger. Can leverage Google Picker API or build custom tree browser against Drive API `files().list()` |
| DR9 | Provenance metadata schema | **Missing** | High | No source tracking for imported files. Needs a `file_provenance` table linking imported workbooks to their Drive source: `drive_file_id`, `drive_file_name`, `drive_folder_id`, `imported_at`, `imported_by`, `source_modified_at`, `source_md5` |
| DR10 | Style/color export parity | **Partial** | Medium | SheetJS (community edition) handles basic cell styles (bold, borders, number formats). Full color/fill/conditional-formatting parity may require SheetJS Pro or a server-side library like `openpyxl`. Red/green/yellow cell coloring used in governance must survive round-trip |

---

## 3. Prerequisites

Before implementation can begin, the following must be completed:

### 3.1 Google Cloud Console Configuration
- Enable the **Google Drive API** on the existing OAuth project (same project used for Google login)
- Add Drive scopes to the **OAuth consent screen**: `https://www.googleapis.com/auth/drive.readonly`, `https://www.googleapis.com/auth/drive.file`
- Verify the OAuth consent screen is in production mode (not test mode) or add test users during development
- No new OAuth credentials needed — reuse the existing `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`

### 3.2 Server Dependencies
- Install `google-api-python-client` — Drive API client
- Install `google-auth-httplib2` — HTTP transport for Google auth
- Install `google-auth-oauthlib` — OAuth 2.0 flow helpers (may already be partially present from login flow)
- Add all three to `requirements.txt`

### 3.3 Database Migrations
Two new tables required:

**`drive_connections`** — stores per-user Drive OAuth grants
- `id` (TEXT, ULID primary key, `drc_` prefix)
- `user_id` (TEXT, FK to users)
- `workspace_id` (TEXT, FK to workspaces)
- `google_email` (TEXT)
- `encrypted_refresh_token` (TEXT)
- `scopes_granted` (TEXT[])
- `connected_at` (TIMESTAMPTZ)
- `last_used_at` (TIMESTAMPTZ)
- `revoked_at` (TIMESTAMPTZ, nullable)

**`file_provenance`** — tracks Drive source for imported files
- `id` (TEXT, ULID primary key, `fpv_` prefix)
- `document_id` (TEXT, FK to documents)
- `contract_id` (TEXT, FK to contracts)
- `workspace_id` (TEXT, FK to workspaces)
- `source_type` (TEXT, enum: `google_drive`, `local_upload`)
- `drive_file_id` (TEXT, nullable)
- `drive_file_name` (TEXT, nullable)
- `drive_folder_id` (TEXT, nullable)
- `drive_mime_type` (TEXT, nullable)
- `source_modified_at` (TIMESTAMPTZ, nullable)
- `source_md5` (TEXT, nullable)
- `imported_at` (TIMESTAMPTZ)
- `imported_by` (TEXT, FK to users)
- `import_version` (INTEGER, default 1)

### 3.4 Environment Variables
- No new secrets required — reuse `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`
- Optional: `DRIVE_ENCRYPTION_KEY` for encrypting stored refresh tokens at rest

---

## 4. Risk Register

| # | Risk | Impact | Likelihood | Mitigation |
|---|------|--------|-----------|-----------|
| DRK1 | SheetJS style parity limitations | Medium | Medium | Test round-trip with representative governance workbooks (red/green/yellow cells). If community SheetJS drops styles, evaluate SheetJS Pro license or `openpyxl` server-side fallback |
| DRK2 | OAuth scope creep / user consent fatigue | Low | Medium | Request only `drive.readonly` and `drive.file` (minimal scopes). Explain scope purpose in consent screen. Use incremental authorization so Drive scopes are requested only when user first connects Drive, not at login |
| DRK3 | Shared Drive permission complexity | Medium | Low | Shared Drives (Team Drives) have different permission models than My Drive. Initially support My Drive only; Shared Drive support as a follow-on. Document limitation clearly in UI |
| DRK4 | Large file handling (>50MB) | Low | Low | Drive API supports resumable uploads for files >5MB. Set a 50MB import limit in v1; display clear error for oversized files. Most contract workbooks are <10MB |
| DRK5 | Token refresh race conditions | Medium | Low | If multiple requests attempt to refresh an expired access token simultaneously, use database-level locking (SELECT FOR UPDATE) on the `drive_connections` row to serialize refresh attempts |
| DRK6 | Drive API quota limits | Low | Low | Default Drive API quota is 20,000 requests/100 seconds. Manual-refresh-only model keeps request volume low. Monitor via Google Cloud Console |
| DRK7 | Revoked access mid-session | Medium | Low | User may revoke Drive access via Google Account settings. API calls will return 401. Handle gracefully: clear stored tokens, prompt re-authorization, emit `drive.disconnect` audit event |

---

## 5. Dependency Map

```
                    ┌─────────────────────────┐
                    │  Google Cloud Console    │
                    │  (Enable Drive API +     │
                    │   OAuth scope update)    │
                    └────────────┬────────────┘
                                 │
                    ┌────────────▼────────────┐
                    │  DR1: OAuth Infra        │
                    │  (Add Drive scopes to    │
                    │   auth_google.py)        │
                    └────────────┬────────────┘
                                 │
              ┌──────────────────┼──────────────────┐
              │                  │                  │
    ┌─────────▼─────────┐ ┌─────▼─────────┐ ┌─────▼──────────┐
    │ DR2: Token Storage │ │ DR3: Drive    │ │ DR6: Audit     │
    │ (drive_connections │ │ API Client    │ │ Events         │
    │  table + refresh)  │ │ (pip install) │ │ (new types)    │
    └─────────┬─────────┘ └─────┬─────────┘ └────────────────┘
              │                 │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  Drive API      │
              │  Service Layer  │
              │  (list, get,    │
              │   download,     │
              │   upload)       │
              └────────┬────────┘
                       │
         ┌─────────────┼─────────────┐
         │             │             │
   ┌─────▼──────┐ ┌───▼──────┐ ┌───▼──────────┐
   │ DR4: Import │ │ DR5:     │ │ DR9:         │
   │ Pipeline    │ │ Export   │ │ Provenance   │
   │ (connect to │ │ Pipeline │ │ Metadata     │
   │  existing)  │ │ (upload) │ │ (file_prov.) │
   └─────────────┘ └──────────┘ └──────────────┘
                       │
              ┌────────▼────────┐
              │  DR8: Drive     │
              │  Browser UI     │
              │  (file picker)  │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  DR7: RBAC      │
              │  (Drive-specific│
              │   permissions)  │
              └────────┬────────┘
                       │
              ┌────────▼────────┐
              │  DR10: Style    │
              │  Export Parity  │
              │  (round-trip)   │
              └─────────────────┘
```

**Implementation ordering (recommended):**
1. Google Cloud Console setup (prerequisite, non-code)
2. DR3 → DR1 → DR2 (server foundation: library, scopes, token storage)
3. DR6 (audit events — wire early so all subsequent work is auditable)
4. DR9 (provenance schema — needed before import)
5. DR4 → DR5 (import then export pipelines)
6. DR7 (RBAC rules for Drive operations)
7. DR8 (UI file picker — last, depends on all backend work)
8. DR10 (style parity testing — iterative, can parallel with DR8)

---

## 6. Estimated Effort

| Phase | Description | Estimate | Dependencies |
|-------|------------|----------|-------------|
| P0 | Google Cloud Console config + library install | 0.5 day | None |
| P1 | OAuth scope expansion + token storage migration | 1–2 days | P0 |
| P2 | Drive API service layer (list/get/download/upload) | 2–3 days | P1 |
| P3 | Import pipeline integration + provenance tracking | 1–2 days | P2 |
| P4 | Export pipeline (status-based naming + Drive upload) | 1–2 days | P2 |
| P5 | Audit event types + RBAC rules for Drive | 1 day | P2 |
| P6 | Drive file browser UI component | 2–3 days | P2, P5 |
| P7 | Style/color export parity testing + fixes | 1–2 days | P4 |
| P8 | Integration testing + edge cases | 1–2 days | All |
| **Total** | | **10–17 days** | |

---

## 7. Cross-References

- `docs/handoff/V25_READINESS_REPORT.md` — V2.5 core readiness audit
- `docs/decisions/DECISION_V25_DB.md` — PostgreSQL canonical database decision
- `docs/decisions/DECISION_V25_DRIVE_SCOPE.md` — Drive integration scope decision
- `docs/features/V25_GOOGLE_DRIVE_INTEGRATION.md` — Feature specification
- `docs/api/API_SPEC_V2_5_CANONICAL.md` — API contract
- `server/routes/auth_google.py` — Existing Google OAuth implementation
- `server/audit.py` — Audit event emission
- `server/auth.py` — RBAC middleware
