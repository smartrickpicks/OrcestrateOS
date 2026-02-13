# V2.5 Google Drive — Gate 3 Alignment Packet

**Version:** 1.0
**Date:** 2026-02-13
**Status:** Gate 3 Complete — Requesting GO
**Gate 1 Approved:** 2026-02-13
**Gate 2 Approved:** 2026-02-13

---

## 1. Final Task Plan

### New Tasks Added at Gate 3

Three requirement blocks added per product owner directive. Task IDs follow the V25-DRV-1xx/2xx/3xx convention, using the 160–179 range (Session Continuity), 180–184 range (Drive Versioning Acceptance), and 190–194 range (Top-Pane Source UX).

---

#### Block A: Session Continuity (V25-DRV-160 through V25-DRV-169)

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-DRV-160 | P0 | BE | None | Pending | DB migration adds `workbook_sessions` table: `id` (TEXT PK, `wbs_` prefix), `user_id` (TEXT FK), `workspace_id` (TEXT FK), `environment` (TEXT: 'sandbox'/'production'), `source_type` (TEXT: 'local'/'drive'), `source_ref` (TEXT: file path or Drive file ID), `session_data` (JSONB: workbook state blob), `status` (TEXT: 'active'/'archived'/'deleted'), `created_at` (TIMESTAMPTZ), `updated_at` (TIMESTAMPTZ), `last_accessed_at` (TIMESTAMPTZ). Dedupe unique constraint on `(user_id, workspace_id, environment, source_type, source_ref)` |
| V25-DRV-161 | P0 | BE | DRV-160 | Pending | API endpoints: `GET /sessions/active` returns most recent active session for current user+workspace+environment; `POST /sessions` creates new session (checks dedupe key first — returns existing if match found); `PATCH /sessions/{id}` updates session_data or status; `DELETE /sessions/{id}` soft-deletes (sets status='deleted') |
| V25-DRV-162 | P0 | FE | DRV-161 | Pending | Auto-resume on login: after JWT auth resolves, call `GET /sessions/active`; if valid session exists, restore workbook state from `session_data` without re-upload/re-import. User sees their last working state within 2 seconds of login |
| V25-DRV-163 | P0 | FE | DRV-162 | Pending | No new session on re-login: if user logs out and back in, the same session resumes (matched by dedupe key). New session only created when: (a) user explicitly clicks "New Session", (b) no prior session exists for dedupe key, or (c) user loads a different file |
| V25-DRV-164 | P0 | FE | DRV-162 | Pending | Source-aware resume: for `source_type='local'`, session stores workbook bytes in IndexedDB keyed by session ID + file hash; for `source_type='drive'`, session stores `drive_import_id` (provenance ref) and re-fetches bytes from server cache or Drive on resume |
| V25-DRV-165 | P0 | FE | DRV-163 | Pending | Session controls UI: session management dropdown (accessible from source badge area) with five actions: "Resume Last" (default on login), "New Session" (prompts file source selection), "Archive" (sets status='archived', clears from active), "Delete" (soft-delete with confirmation), "Clear Archived" (bulk delete archived sessions) |
| V25-DRV-166 | P1 | BE | DRV-161 | Pending | `GET /sessions` list endpoint: returns all sessions for user+workspace with status filter param (`?status=active,archived`). Supports cursor pagination |
| V25-DRV-167 | P1 | FE | DRV-166 | Pending | Session history panel: shows list of archived sessions with source info, last accessed time, and "Restore" action (sets status back to 'active') |
| V25-DRV-168 | P0 | BE | DRV-161 | Pending | Session auto-save: `PATCH /sessions/{id}` called on workbook auto-save interval (every 30s) with updated `session_data` blob and `last_accessed_at` timestamp |
| V25-DRV-169 | P1 | BE | DRV-160 | Pending | Audit events: `SESSION_CREATED`, `SESSION_RESUMED`, `SESSION_ARCHIVED`, `SESSION_DELETED` emitted with session ID, source_type, source_ref, user_id |

---

#### Block B: Drive Refresh / Versioning Acceptance (V25-DRV-180 through V25-DRV-184)

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-DRV-180 | P0 | BE | DRV-121, DRV-122 | Pending | Import provenance schema includes `version_number` (INTEGER NOT NULL DEFAULT 1), `supersedes_id` (TEXT FK → self). Unique constraint on `(workspace_id, source_file_id, version_number)`. Index on `(workspace_id, source_file_id, version_number DESC)` |
| V25-DRV-181 | P0 | BE | DRV-180 | Pending | `POST /drive/import` auto-increments `version_number` per workspace+source_file_id pair. Response includes `version_number` and `supersedes_id`. If source_file_id already imported, new record created with `supersedes_id` pointing to previous version |
| V25-DRV-182 | P0 | BE | DRV-181 | Pending | `GET /drive/import-history?source_file_id={id}` returns all versions ordered by version_number DESC with fields: `import_id`, `version_number`, `imported_at`, `imported_by`, `supersedes_id`, `is_current` (boolean: true for latest). Requires workspace auth |
| V25-DRV-183 | P0 | FE | DRV-182 | Pending | "Refresh from Drive" UI shows confirmation: "This will create Version N of {filename}. Your current working copy (Version N-1) will be preserved." Triggers new import (not replace). Version badge shown on source indicator |
| V25-DRV-184 | P0 | BE+FE | DRV-181 | Pending | No destructive replace path: system has no API or UI affordance that overwrites or deletes a previous imported version. `DELETE` on import provenance records is not exposed. Verification: attempt to find any code path that mutates an existing provenance row's core fields (source_file_id, version_number, source content) — must find none |

---

#### Block C: Top-Pane Source UX (V25-DRV-190 through V25-DRV-194)

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-DRV-190 | P0 | FE | None | Pending | Top-pane data source area shows two primary CTAs: "Upload Local Excel" (opens file picker for .xlsx/.xls/.csv) and "Connect/Open from Google Drive" (initiates Drive flow if not connected, or opens Drive browser if connected). Both are always visible when no workbook is loaded |
| V25-DRV-191 | P0 | FE | DRV-190, DRV-123 | Pending | Active source badge: after workbook loads, top-pane collapses to a compact badge showing source type ("Local: filename.xlsx" or "Drive: filename.xlsx") with dropdown for session controls |
| V25-DRV-192 | P1 | BE | DRV-160 | Pending | Default source preference: persist user's last-used source type per workspace in `workbook_sessions` table. On next visit, pre-highlight the matching CTA (visual hint only, not auto-action) |
| V25-DRV-193 | P1 | FE | DRV-191 | Pending | Source badge dropdown includes: "Switch Source" (shows both CTAs again), "Refresh from Drive" (if Drive source), session controls (Resume/New/Archive/Delete) |
| V25-DRV-194 | P0 | FE | DRV-190 | Pending | Empty state: when no workbook loaded and no resumable session, show centered panel with both CTAs and brief helper text. When resumable session exists, show "Resume Last Session" as primary action above the two CTAs |

---

## 2. Complete Task Inventory (All Phases)

### Summary with New Blocks

| Phase | Task Range | P0 | P1 | P2 | Total |
|-------|-----------|----|----|-----|-------|
| DRV-1: OAuth + Connection | 100–105 | 4 | 2 | 0 | 6 |
| DRV-2: Drive Browser | 110–115 | 3 | 1 | 1 | 5 |
| DRV-3: Import Pipeline | 120–125 | 3 | 2 | 1 | 6 |
| DRV-4: Export / Save to Drive | 130–136 | 4 | 2 | 0 | 6 |
| DRV-5: Audit + Governance | 140–145 | 4 | 1 | 0 | 5 |
| DRV-6: UI Integration | 150–153 | 1 | 2 | 1 | 4 |
| **NEW** DRV-7: Session Continuity | 160–169 | 6 | 4 | 0 | 10 |
| **NEW** DRV-8: Drive Versioning | 180–184 | 5 | 0 | 0 | 5 |
| **NEW** DRV-9: Top-Pane Source UX | 190–194 | 3 | 2 | 0 | 5 |
| **Grand Total** | | **33** | **16** | **3** | **52** |

---

## 3. Sequencing Lock

### Implementation Order

```
LAYER 0 — Foundation (no dependencies)
  V25-DRV-100  google-api-python-client dependency
  V25-DRV-121  Provenance schema migration
  V25-DRV-160  Session table migration
  V25-DRV-190  Top-pane dual CTA UI (static, no backend)

LAYER 1 — OAuth + Session Backend (depends on Layer 0)
  V25-DRV-101  Drive connect endpoint         ← DRV-100
  V25-DRV-161  Session CRUD endpoints         ← DRV-160
  V25-DRV-180  Versioned provenance schema    ← DRV-121

LAYER 2 — OAuth Completion + Session Frontend (depends on Layer 1)
  V25-DRV-102  OAuth callback + token storage  ← DRV-101
  V25-DRV-162  Auto-resume on login            ← DRV-161
  V25-DRV-163  No-new-session-on-relogin       ← DRV-162
  V25-DRV-165  Session controls UI             ← DRV-163
  V25-DRV-168  Session auto-save               ← DRV-161
  V25-DRV-194  Empty state / resume panel      ← DRV-190

LAYER 3 — Drive Operations (depends on Layer 2)
  V25-DRV-103  Token refresh handler           ← DRV-102
  V25-DRV-104  Disconnect endpoint             ← DRV-102
  V25-DRV-105  Connection status endpoint      ← DRV-102
  V25-DRV-140  DRIVE_CONNECTED audit           ← DRV-102
  V25-DRV-164  Source-aware resume             ← DRV-162
  V25-DRV-181  Versioned import logic          ← DRV-180

LAYER 4 — Browse + Import (depends on Layer 3)
  V25-DRV-110  Shared drive listing            ← DRV-103
  V25-DRV-120  Server-side file download       ← DRV-103
  V25-DRV-141  DRIVE_DISCONNECTED audit        ← DRV-104
  V25-DRV-182  Import history endpoint         ← DRV-181
  V25-DRV-169  Session audit events            ← DRV-160

LAYER 5 — Browser + Import Pipeline (depends on Layer 4)
  V25-DRV-111  Folder listing                  ← DRV-110
  V25-DRV-122  Import endpoint                 ← DRV-120, DRV-121, DRV-181
  V25-DRV-166  Session list endpoint           ← DRV-161

LAYER 6 — Browser UI + Import UI (depends on Layer 5)
  V25-DRV-112  File filtering                  ← DRV-111
  V25-DRV-123  Source badge UI                 ← DRV-122
  V25-DRV-125  Red-cell detection              ← DRV-122
  V25-DRV-143  DRIVE_FILE_IMPORTED audit       ← DRV-122
  V25-DRV-183  Refresh confirmation UI         ← DRV-182
  V25-DRV-184  No destructive replace verify   ← DRV-181

LAYER 7 — Browser Completion (depends on Layer 6)
  V25-DRV-113  Drive browser UI modal          ← DRV-112
  V25-DRV-142  DRIVE_FILE_BROWSED audit        ← DRV-111
  V25-DRV-191  Active source badge             ← DRV-190, DRV-123
  V25-DRV-167  Session history panel           ← DRV-166

LAYER 8 — Data Pane + Export (depends on Layer 7)
  V25-DRV-114  "Connect from Drive" button     ← DRV-113
  V25-DRV-115  Manual refresh action           ← DRV-113
  V25-DRV-130  Export toggle UI                ← DRV-122
  V25-DRV-124  Provenance display              ← DRV-122
  V25-DRV-192  Default source preference       ← DRV-160
  V25-DRV-193  Source badge dropdown           ← DRV-191

LAYER 9 — Export Pipeline (depends on Layer 8)
  V25-DRV-131  Filename convention             ← DRV-130
  V25-DRV-150  Data pane dual source           ← DRV-114
  V25-DRV-151  Source badge integration        ← DRV-123
  V25-DRV-153  Drive status indicator          ← DRV-105
  V25-DRV-152  Provenance panel                ← DRV-124

LAYER 10 — Export Completion (depends on Layer 9)
  V25-DRV-132  Server-side Drive upload        ← DRV-103, DRV-131
  V25-DRV-136  No-overwrite guard              ← DRV-132

LAYER 11 — Export Endpoints + Audit (depends on Layer 10)
  V25-DRV-133  Export endpoint                 ← DRV-132
  V25-DRV-134  Changes log artifact            ← DRV-133
  V25-DRV-135  Style/color parity              ← DRV-133
  V25-DRV-144  DRIVE_EXPORT_SAVED audit        ← DRV-133
  V25-DRV-145  DRIVE_EXPORT_FINALIZED audit    ← DRV-133
```

### Sequencing Impact of New Blocks

| New Block | Inserts At | Affects | Notes |
|-----------|-----------|---------|-------|
| Session Continuity (DRV-7) | Layers 0–4 | Parallel with OAuth; no blocking on Drive code | Session table + endpoints can be built concurrently with Drive OAuth |
| Drive Versioning (DRV-8) | Layers 1–6 | DRV-180 depends on DRV-121 (provenance schema); DRV-181 gates import endpoint | Versioning fields added to same migration as provenance; minimal sequencing impact |
| Top-Pane Source UX (DRV-9) | Layers 0, 7–9 | DRV-190 (static UI) has no dependencies; DRV-191/193 depend on source badge | Static CTA UI can ship in Layer 0; wired behavior follows |

---

## 4. Contract Freeze Summary

All Gate 1 + Gate 2 decisions remain frozen. Gate 3 adds:

| Item | Lock |
|------|------|
| Session dedupe key | `(user_id, workspace_id, environment, source_type, source_ref)` — unique constraint |
| Session auto-resume | Default on login; no new session unless explicit or no match |
| Session controls | Resume Last / New / Archive / Delete / Clear Archived |
| Drive refresh model | Create new version; no replace; no destructive path |
| Import history | GET endpoint required and tested |
| Top-pane CTAs | "Upload Local Excel" + "Connect/Open from Google Drive" |
| Source badge | Persistent per user+workspace via session table |

---

## 5. Test / Verification Plan

### 5.1 Session Dedupe Tests

| Test ID | Test Case | Expected Result | Priority |
|---------|-----------|-----------------|----------|
| T-SES-01 | User uploads local file `contracts.xlsx` in sandbox → session created | Session row exists with `source_type='local'`, `source_ref='contracts.xlsx'`, `environment='sandbox'` | P0 |
| T-SES-02 | Same user re-uploads same file `contracts.xlsx` in same workspace+environment | No new session created; existing session returned (dedupe key match) | P0 |
| T-SES-03 | Same user uploads DIFFERENT file `billing.xlsx` in same workspace+environment | New session created (different `source_ref`) | P0 |
| T-SES-04 | Same user uploads same file in PRODUCTION environment | New session created (different `environment`) | P0 |
| T-SES-05 | Different user uploads same file in same workspace+environment | New session created (different `user_id`) | P0 |
| T-SES-06 | User imports file from Drive (`source_type='drive'`, `source_ref=DRIVE_FILE_ID`) | Session created with `source_type='drive'` | P0 |
| T-SES-07 | Same user re-imports same Drive file | Existing session returned (dedupe key match) | P0 |
| T-SES-08 | User imports different Drive file | New session created | P0 |
| T-SES-09 | Attempt to create session with duplicate dedupe key via API | API returns existing session (200), not error | P0 |
| T-SES-10 | Delete session, then re-create with same dedupe key | New session created (soft-deleted sessions don't block dedupe) | P1 |

### 5.2 Auto-Resume Tests

| Test ID | Test Case | Expected Result | Priority |
|---------|-----------|-----------------|----------|
| T-RES-01 | User logs in with valid JWT, has active session | Workbook auto-restores from session_data; user sees last working state | P0 |
| T-RES-02 | User logs in with valid JWT, no active session | Empty state shown with dual CTAs | P0 |
| T-RES-03 | User logs in, has active session, clicks "New Session" | Current session archived; new empty state shown with dual CTAs | P0 |
| T-RES-04 | User logs out and logs back in | Same session resumes (not a new session) | P0 |
| T-RES-05 | User has active Drive session, Drive file still accessible | Session resumes; workbook state restored from session_data | P0 |
| T-RES-06 | User has active Drive session, Drive file no longer accessible (deleted/unshared) | Session resumes from cached state; warning shown: "Source file is no longer accessible on Drive. Working copy preserved." | P1 |
| T-RES-07 | User has archived session, clicks "Restore" | Session status set to 'active'; workbook restores | P1 |
| T-RES-08 | Auto-save fires every 30s while working | `PATCH /sessions/{id}` called; `last_accessed_at` updated; `session_data` updated | P0 |
| T-RES-09 | User has multiple archived sessions | Session history panel shows all with source info, last accessed, restore/delete actions | P1 |

### 5.3 Drive Versioning Tests

| Test ID | Test Case | Expected Result | Priority |
|---------|-----------|-----------------|----------|
| T-VER-01 | Import file from Drive (first time) | Provenance row created with `version_number=1`, `supersedes_id=NULL` | P0 |
| T-VER-02 | "Refresh from Drive" on same file | New provenance row with `version_number=2`, `supersedes_id` pointing to v1 | P0 |
| T-VER-03 | Second refresh on same file | `version_number=3`, `supersedes_id` points to v2 | P0 |
| T-VER-04 | `GET /drive/import-history?source_file_id=X` | Returns versions in DESC order; latest has `is_current=true` | P0 |
| T-VER-05 | Attempt to DELETE import provenance record via API | 404 or 405 — no delete endpoint exists | P0 |
| T-VER-06 | Attempt to PATCH provenance record's `source_file_id` or `version_number` | 400 or 405 — immutable fields cannot be changed | P0 |
| T-VER-07 | Verify no code path updates existing provenance row's core fields | Static analysis / grep confirms no UPDATE on provenance core columns | P0 |

### 5.4 Top-Pane UX Tests

| Test ID | Test Case | Expected Result | Priority |
|---------|-----------|-----------------|----------|
| T-UX-01 | No workbook loaded, no session | Two CTAs visible: "Upload Local Excel" and "Connect/Open from Google Drive" | P0 |
| T-UX-02 | Resumable session exists | "Resume Last Session" shown as primary; two CTAs shown below | P0 |
| T-UX-03 | Workbook loaded from local file | Top-pane collapses to badge: "Local: filename.xlsx" with dropdown | P0 |
| T-UX-04 | Workbook loaded from Drive | Top-pane collapses to badge: "Drive: filename.xlsx" with dropdown | P0 |
| T-UX-05 | Click "Switch Source" in badge dropdown | Badge expands back to dual CTA view | P1 |

### 5.5 Existing Gate 5 Criteria (Unchanged)

All 11 original Gate 5 validation criteria remain in force. The tests above supplement, not replace, those criteria.

---

## 6. Risk Register

| ID | Risk | Impact | Likelihood | Mitigation |
|----|------|--------|------------|------------|
| DRK-1 | SheetJS style parity limitations | Low | Medium | D4 accepts; known gaps documented |
| DRK-2 | OAuth scope creep | Low | Low | D1 locks exact scopes |
| DRK-3 | Shared Drive permission complexity | Low | Low | D3 locks hard-fail UX |
| DRK-4 | Large file handling (>50MB) | Low | Low | D5 sets 50MB cap |
| DRK-5 | Token refresh race conditions | Medium | Low | Single-writer pattern; mutex on refresh |
| DRK-6 | Shared Drive API differences | Medium | Low | `supportsAllDrives=true` on all API calls |
| DRK-7 | Migration complexity (3 new tables) | Medium | Low | Tables are additive; no ALTER on existing tables |
| DRK-8 | Versioned import storage growth | Medium | Low | Metadata-only storage; no file bytes on server |
| DRK-9 | Two-scope OAuth consent | Low | Low | Clear consent messaging |
| **DRK-10** (NEW) | Session data blob size | Medium | Medium | JSONB column; cap `session_data` at 5MB; prune old auto-saves |
| **DRK-11** (NEW) | IndexedDB + server session sync conflicts | Medium | Low | Server is authoritative; IndexedDB is warm cache only; last-write-wins on PATCH |
| **DRK-12** (NEW) | Auto-resume with stale session data | Low | Medium | `last_accessed_at` shown to user; "stale session" warning if >24h old |

---

## 7. Go / No-Go Assessment

| Criterion | Status |
|-----------|--------|
| All product decisions locked (D1–D7) | GO |
| Task plan complete (52 tasks, 33 P0) | GO |
| Sequencing dependencies mapped (12 layers) | GO |
| Test plan covers session dedupe, auto-resume, versioning, UX | GO |
| Risk register updated with session-specific risks | GO |
| No unresolved blockers | GO |
| Gate 1 + Gate 2 contracts preserved | GO |

---

**Requesting APPROVE GATE 3 / START CODE**
