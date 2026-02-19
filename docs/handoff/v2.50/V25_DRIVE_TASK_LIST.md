# V2.5 Google Drive Integration — Task List

**Version:** 0.1 (Gate 1 — Docs Only)
**Date:** 2026-02-13
**Status:** Gate 1 (Docs) — No code changes

---

## Task Dependency Graph

```
Phase DRV-1: OAuth + Connection
  V25-DRV-100 google-api-python-client ──→ V25-DRV-101 Connect endpoint
                                              │
                                              └──→ V25-DRV-102 Callback + token storage
                                                      │
                                                      ├──→ V25-DRV-103 Token refresh handler
                                                      │       │
                                                      │       │   Phase DRV-2: Drive Browser
                                                      │       ├──→ V25-DRV-110 Shared drive listing
                                                      │       │       └──→ V25-DRV-111 Folder listing
                                                      │       │               │
                                                      │       │               ├──→ V25-DRV-112 File filtering
                                                      │       │               │       └──→ V25-DRV-113 Browser UI
                                                      │       │               │               ├──→ V25-DRV-114 "Connect from Drive" button
                                                      │       │               │               └──→ V25-DRV-115 Manual refresh action
                                                      │       │               │
                                                      │       │               └──→ V25-DRV-142 DRIVE_FILE_BROWSED audit
                                                      │       │
                                                      │       │   Phase DRV-3: Import Pipeline
                                                      │       └──→ V25-DRV-120 Server-side file download
                                                      │               │
                                                      │               └──→ V25-DRV-122 Import endpoint ←── V25-DRV-121 Provenance schema (no deps)
                                                      │                       │
                                                      │                       ├──→ V25-DRV-123 Source badge UI
                                                      │                       ├──→ V25-DRV-124 Provenance display
                                                      │                       ├──→ V25-DRV-125 Red-cell detection
                                                      │                       ├──→ V25-DRV-143 DRIVE_FILE_IMPORTED audit
                                                      │                       │
                                                      │                       │   Phase DRV-4: Export/Save to Drive
                                                      │                       └──→ V25-DRV-130 Export toggle UI
                                                      │                               └──→ V25-DRV-131 Filename convention
                                                      │                                       └──→ V25-DRV-132 Server-side upload ←── DRV-103
                                                      │                                               │
                                                      │                                               ├──→ V25-DRV-133 Export endpoint
                                                      │                                               │       ├──→ V25-DRV-134 Changes log artifact
                                                      │                                               │       ├──→ V25-DRV-135 Style/color parity
                                                      │                                               │       ├──→ V25-DRV-144 DRIVE_EXPORT_SAVED audit
                                                      │                                               │       └──→ V25-DRV-145 DRIVE_EXPORT_FINALIZED audit
                                                      │                                               │
                                                      │                                               └──→ V25-DRV-136 No-overwrite guard
                                                      │
                                                      ├──→ V25-DRV-104 Disconnect endpoint
                                                      │       └──→ V25-DRV-141 DRIVE_DISCONNECTED audit
                                                      │
                                                      ├──→ V25-DRV-105 Connection status endpoint
                                                      │
                                                      └──→ V25-DRV-140 DRIVE_CONNECTED audit

Phase DRV-6: UI Integration
  V25-DRV-150 Data pane dual source ←── DRV-114
  V25-DRV-151 Source badge ←── DRV-123
  V25-DRV-152 Provenance panel ←── DRV-124
  V25-DRV-153 Drive status indicator ←── DRV-105
```

---

## Phase DRV-1: OAuth + Connection

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-DRV-100 | P0 | BE | None | Pending | `google-api-python-client` and `google-auth-oauthlib` added to `requirements.txt`, importable in server environment |
| V25-DRV-101 | P0 | BE | DRV-100 | Pending | `POST /drive/connect` initiates Drive-scoped OAuth flow, returns `{ auth_url }` for client redirect |
| V25-DRV-102 | P0 | BE | DRV-101 | Pending | OAuth callback stores encrypted refresh token in `user_drive_tokens` table; existing Google OAuth session reused |
| V25-DRV-103 | P0 | BE | DRV-102 | Pending | Expired access tokens auto-refresh before any Drive API call; transparent to caller |
| V25-DRV-104 | P1 | BE | DRV-102 | Pending | `DELETE /drive/disconnect` revokes token via Google API, deletes row from `user_drive_tokens` |
| V25-DRV-105 | P1 | BE | DRV-102 | Pending | `GET /drive/status` returns `{ connected: bool, email, drive_user }` for current session user |

---

## Phase DRV-2: Drive Browser

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-DRV-110 | P0 | BE | DRV-103 | Pending | `GET /drive/browse?type=drives` returns list of shared drives accessible to user |
| V25-DRV-111 | P0 | BE | DRV-110 | Pending | `GET /drive/browse?parent=FOLDER_ID` returns folders + files with name, mimeType, modifiedTime, size |
| V25-DRV-112 | P0 | BE | DRV-111 | Pending | Response filtered to `.xlsx`, `.xls`, `.csv` files only; folders always included for navigation |
| V25-DRV-113 | P0 | FE | DRV-112 | Pending | Modal with breadcrumb navigation, folder drill-down, file selection; loading states; error handling |
| V25-DRV-114 | P1 | FE | DRV-113 | Pending | Data source drawer shows "Upload Local File" and "Connect from Drive" options side-by-side |
| V25-DRV-115 | P2 | FE | DRV-113 | Pending | "Refresh from Drive" action re-fetches file from Drive, prompts merge/replace for working copy |

---

## Phase DRV-3: Import Pipeline

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-DRV-120 | P0 | BE | DRV-103 | Pending | Server fetches file bytes from Drive API using `files.get(media)`, streams to memory |
| V25-DRV-121 | P0 | BE | None | Pending | Migration adds `source_provenance` table with columns: `id`, `workspace_id`, `source_file_id`, `drive_id`, `version`, `imported_at`, `imported_by`, `has_external_modifications`, `baseline_unknown`, `filename`, `mime_type` |
| V25-DRV-122 | P0 | BE | DRV-120, DRV-121 | Pending | `POST /drive/import` creates provenance snapshot row, returns file bytes for client workbook pipeline |
| V25-DRV-123 | P1 | FE | DRV-122 | Pending | Loaded workbook displays "Local" or "Drive" badge based on source_provenance |
| V25-DRV-124 | P2 | FE | DRV-122 | Pending | Record inspector shows `imported_at`, `imported_by`, source file name, Drive link |
| V25-DRV-125 | P1 | BE | DRV-122 | Pending | On import, scan for pre-colored (red) cells; set `has_external_modifications = true` if detected |

---

## Phase DRV-4: Export / Save to Drive

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-DRV-130 | P0 | FE | DRV-122 | Pending | Two-button export UI: "Save In Progress" (Analyst+) and "Export Final" (Verifier+); role-based visibility enforced |
| V25-DRV-131 | P0 | BE | DRV-130 | Pending | Filename convention: `[STATUS] Original_Name_YYYY-MM-DD.xlsx` where STATUS is role-derived (`IN_PROGRESS`, `VERIFIED`, `APPROVED`) |
| V25-DRV-132 | P0 | BE | DRV-103, DRV-131 | Pending | Server uploads file bytes to Drive via `files.create` API; returns `{ file_id, web_view_link }` |
| V25-DRV-133 | P0 | BE | DRV-132 | Pending | `POST /drive/export` accepts workbook bytes + metadata, applies naming convention, uploads to target folder |
| V25-DRV-134 | P1 | BE | DRV-133 | Pending | Generate major-changes log as separate sheet or companion file; include in export payload |
| V25-DRV-135 | P1 | BE | DRV-133 | Pending | Exported workbook preserves cell styles, colors, formatting from working copy |
| V25-DRV-136 | P0 | BE | DRV-132 | Pending | Never silently overwrite source file; always create new file or append version suffix to filename |

---

## Phase DRV-5: Audit + Governance

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-DRV-140 | P0 | BE | DRV-102 | Pending | `DRIVE_CONNECTED` audit event emitted on successful OAuth connect with user_id, drive_email |
| V25-DRV-141 | P0 | BE | DRV-104 | Pending | `DRIVE_DISCONNECTED` audit event emitted on disconnect with user_id, drive_email |
| V25-DRV-142 | P1 | BE | DRV-111 | Pending | `DRIVE_FILE_BROWSED` audit event emitted on folder navigation; debounced (max 1 per folder per 5s) |
| V25-DRV-143 | P0 | BE | DRV-122 | Pending | `DRIVE_FILE_IMPORTED` audit event emitted with provenance snapshot (file_id, drive_id, version, user_id) |
| V25-DRV-144 | P0 | BE | DRV-133 | Pending | `DRIVE_EXPORT_SAVED` audit event emitted on Save In Progress with file_id, target_folder, user_id |
| V25-DRV-145 | P0 | BE | DRV-133 | Pending | `DRIVE_EXPORT_FINALIZED` audit event emitted on Export Final with file_id, target_folder, user_id, status |

---

## Phase DRV-6: UI Integration

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-DRV-150 | P0 | FE | DRV-114 | Pending | Data pane supports dual source: "Upload Local File" and "Connect from Drive" with unified post-load pipeline |
| V25-DRV-151 | P1 | FE | DRV-123 | Pending | Visual badge indicator showing "Local" or "Drive" on active workbook; tooltip shows source details |
| V25-DRV-152 | P2 | FE | DRV-124 | Pending | Provenance panel in record inspector shows imported_at, imported_by, source file name, Drive link |
| V25-DRV-153 | P1 | FE | DRV-105 | Pending | Header/sidebar indicator showing Drive connected/disconnected state with connect/disconnect action |

---

## Summary Table

| Phase | P0 | P1 | P2 | Total |
|-------|----|----|-----|-------|
| DRV-1: OAuth + Connection | 4 | 2 | 0 | 6 |
| DRV-2: Drive Browser | 3 | 1 | 1 | 5 |
| DRV-3: Import Pipeline | 3 | 2 | 1 | 6 |
| DRV-4: Export / Save to Drive | 4 | 2 | 0 | 6 |
| DRV-5: Audit + Governance | 4 | 1 | 0 | 5 |
| DRV-6: UI Integration | 1 | 2 | 1 | 4 |
| **Grand Total** | **19** | **10** | **3** | **32** |
