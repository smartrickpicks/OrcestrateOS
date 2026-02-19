# V2.5 Google Drive — Locked Decisions

**Version:** 1.0
**Date:** 2026-02-13
**Status:** Frozen — Gate 2 Complete

---

## Frozen Decisions

### D1: OAuth Scopes

**Decision:** Use `drive.readonly` for browse/import + `drive.file` for export write-back.

- `https://www.googleapis.com/auth/drive.readonly` — browse all files, download for import
- `https://www.googleapis.com/auth/drive.file` — write only to files created/opened by the app
- Requested together in a single consent screen
- Scope separation from login OAuth preserved (Drive scopes are a separate authorization flow)

**Locked by:** Product owner approval, 2026-02-13

---

### D2: Export Target Folder

**Decision:** Default to source file's parent folder; user may override at export time.

- Export dialog pre-fills with the folder the file was originally imported from
- "Change folder" button opens Drive folder picker for override
- Chosen override is not persisted — resets to source folder on next export
- `target_folder_id` API parameter: optional, defaults to source folder if omitted

**Locked by:** Product owner approval, 2026-02-13

---

### D3: No Write Permission Handling

**Decision:** Hard fail with clear folder reselect UX.

- If user lacks write access to the target folder, server returns HTTP 403 with error code `DRIVE_PERMISSION_DENIED`
- Frontend shows: "You don't have write access to this folder. Please choose a different folder."
- Folder picker reopens automatically on error
- No fallback to a default folder — user must explicitly choose

**Locked by:** Product owner approval, 2026-02-13

---

### D4: Style/Color Export Parity

**Decision:** Accept SheetJS free-tier limitations. Document known gaps.

- Supported: cell fill color, font bold/italic/color, basic borders, number formats, merged cells, column width, row height
- Not supported: conditional formatting rules, data validation dropdowns, images/charts, named ranges
- Partial: cell comments (read OK, write limited)
- Red-cell highlighting (fill color) round-trips correctly — this is the critical governance style
- Re-evaluate if users report unacceptable degradation in exported workbooks

**Locked by:** Product owner approval, 2026-02-13

---

### D5: File Size Limit

**Decision:** 50 MB initial cap.

- Server validates file size before downloading from Drive
- If file exceeds 50MB, return HTTP 413 with error code `FILE_TOO_LARGE`
- Message: "File exceeds the 50MB import limit. Please reduce file size or split into smaller workbooks."
- Cap may be raised in future phases based on usage data and server capacity

**Locked by:** Product owner approval, 2026-02-13

---

### D6: Connection Scope

**Decision:** One Drive connection per workspace.

- `drive_connections` table enforces unique constraint on `workspace_id`
- Connecting a new Google account automatically disconnects the previous one
- Disconnect emits `DRIVE_DISCONNECTED` audit event for the old connection
- All workspace members share the same Drive connection (tokens stored server-side)
- Admin/Architect role required to connect/disconnect

**Locked by:** Product owner approval, 2026-02-13

---

### D7: Refresh Behavior (Versioned Import)

**Decision:** Create new imported version on refresh. Do NOT replace working copy.

- Every "Refresh from Drive" creates a new `drive_import_provenance` record with incremented `version_number`
- Previous versions preserved in database (provenance metadata only, not file bytes)
- New version's `supersedes_id` points to previous version's `import_id`
- User sees confirmation: "This will create Version N of {filename}. Your current working copy (Version N-1) will be preserved."
- Version history accessible from source badge dropdown
- Audit event `DRIVE_FILE_IMPORTED` includes `version_number`, `supersedes_id`, `is_refresh`

**Schema impact:**
- `drive_import_provenance.version_number` (INTEGER NOT NULL DEFAULT 1)
- `drive_import_provenance.supersedes_id` (TEXT NULL FK → self)
- Unique constraint: `(workspace_id, source_file_id, version_number)`

**API impact:**
- Import response includes `version_number` and `supersedes_id`
- New endpoint: GET `/drive/import-history?source_file_id=...` for version listing

**Locked by:** Product owner approval, 2026-02-13

---

## Cross-References

- `docs/handoff/V25_DRIVE_CLARITY_MATRIX.md` — Full clarity matrix with rationale
- `docs/features/V25_GOOGLE_DRIVE_INTEGRATION.md` — Feature specification
- `docs/decisions/DECISION_V25_DRIVE_SCOPE.md` — Scope decisions
- `docs/api/API_SPEC_V2_5_CANONICAL.md` — Canonical API spec (Section 12)
