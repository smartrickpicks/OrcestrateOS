# V2.5 Google Drive — Clarity Matrix

**Version:** 1.0
**Date:** 2026-02-13
**Status:** Gate 2 Complete — All decisions locked
**Gate 1 Approved:** 2026-02-13

---

## 1. Decision Table

| # | Question | Decision | Rationale | Impact |
|---|----------|----------|-----------|--------|
| D1 | **OAuth scopes** | `drive.readonly` for browse + `drive.file` for export | Least privilege: read-only covers browse/import; `drive.file` limits write to app-created files only | Two-scope consent screen; user sees both requested permissions |
| D2 | **Export target folder** | Source folder by default; user can override at export time | Keeps exported artifacts near source for discoverability | Export UI needs folder selector (optional override); API `target_folder_id` parameter remains optional |
| D3 | **No write permission on export target** | Hard fail with clear folder reselect UX | Silent fallback would confuse users; explicit reselect is safer | Frontend must catch 403 from Drive API and show folder picker; backend returns `DRIVE_PERMISSION_DENIED` error code |
| D4 | **Style/color parity** | Accept SheetJS free-tier limitations; document known gaps | SheetJS Pro license cost not justified at this stage; most critical styles (fill colors, font weight) are supported | Known gaps documented in §2 below; re-evaluate if users report unacceptable degradation |
| D5 | **File size limit** | 50 MB initial cap | Matches Google Drive simple upload limit; prevents server memory pressure | Server validates `Content-Length` before download; returns `FILE_TOO_LARGE` with 413 status |
| D6 | **Connection scope** | One Drive connection per workspace | Simplifies token management, aligns with workspace isolation model | `drive_connections` table has unique constraint on `workspace_id`; connecting a new account disconnects the old one |
| D7 | **Refresh behavior** | Create new imported version (do NOT replace working copy) | Safer for auditability — every import is a discrete, traceable event; no silent data loss from overwrite | Schema change: `drive_import_provenance` gains `version_number` column and `supersedes_id` FK; API import response includes `version_number`; UI shows version history |

---

## 2. SheetJS Style Parity — Known Gaps (Decision D4)

| Style Property | SheetJS Free Support | Impact | Workaround |
|----------------|---------------------|--------|------------|
| Cell fill color | Supported (rgb/theme) | None — red-cell highlighting preserved | — |
| Font bold/italic | Supported | None | — |
| Font color | Supported | None | — |
| Cell borders | Supported (basic) | Thin/medium/thick OK; double/dash patterns may degrade | Accept basic borders |
| Number formats | Supported | None | — |
| Conditional formatting | **Not supported** | Conditional format rules lost on re-export | Document as known gap; users must reapply in Excel |
| Data validation (dropdowns) | **Not supported** | Dropdown lists lost | Document as known gap |
| Merged cells | Supported | None | — |
| Column width / row height | Supported | None | — |
| Cell comments/notes | **Partial** — read OK, write limited | Some comments may not round-trip | Document as known gap |
| Images/charts | **Not supported** | Embedded images/charts lost | Document as known gap |
| Named ranges | **Not supported** | Named ranges lost | Document as known gap |

**Acceptance criteria:** Cell fill colors (including red-cell highlighting), font styling, and basic borders must round-trip correctly. Conditional formatting, data validation, images, and charts are documented as out-of-scope for this phase.

---

## 3. Schema/API Changes from Decision D7 (Versioned Import)

Decision D7 (create new version on refresh, don't replace) requires the following changes:

### 3.1 Database Schema Delta

**`drive_import_provenance`** — two new columns:

| Column | Type | Default | Notes |
|--------|------|---------|-------|
| `version_number` | `INTEGER NOT NULL` | `1` | Auto-incremented per workspace+source_file_id pair |
| `supersedes_id` | `TEXT NULL` | `NULL` | FK → `drive_import_provenance.id`; points to previous version |

**New index:**
```sql
CREATE INDEX idx_drv_prov_ws_file_version
  ON drive_import_provenance(workspace_id, source_file_id, version_number DESC);
```

**Unique constraint:**
```sql
ALTER TABLE drive_import_provenance
  ADD CONSTRAINT uq_drv_prov_ws_file_version
  UNIQUE (workspace_id, source_file_id, version_number);
```

### 3.2 API Changes

**POST `/drive/import`** response gains two fields:

```json
{
  "data": {
    "import_id": "drv_...",
    "version_number": 2,
    "supersedes_id": "drv_...",
    "filename": "Contract_Workbook.xlsx",
    ...
  }
}
```

**New endpoint: GET `/drive/import-history`**

Lists all imported versions of a given source file within a workspace.

| Parameter | In | Type | Required | Description |
|-----------|-----|------|----------|-------------|
| `source_file_id` | query | string | Yes | Google Drive file ID |

Response:
```json
{
  "data": {
    "versions": [
      {
        "import_id": "drv_...",
        "version_number": 2,
        "imported_at": "2026-02-13T12:00:00Z",
        "imported_by": "usr_...",
        "supersedes_id": "drv_...",
        "is_current": true
      },
      {
        "import_id": "drv_...",
        "version_number": 1,
        "imported_at": "2026-02-12T10:00:00Z",
        "imported_by": "usr_...",
        "supersedes_id": null,
        "is_current": false
      }
    ]
  },
  "meta": { ... }
}
```

### 3.3 UI Impact

- "Refresh from Drive" button triggers a new import, not a replace
- Import confirmation dialog shows: "This will create Version N of {filename}. Your current working copy (Version N-1) will be preserved."
- Version history panel accessible from source badge dropdown
- Current version badge: "v2 (imported 2h ago)"

### 3.4 Audit Event Delta

`DRIVE_FILE_IMPORTED` event gains fields:
- `version_number`: integer
- `supersedes_id`: string | null
- `is_refresh`: boolean (true if version_number > 1)

---

## 4. Risk Register Deltas (Changes from Gate 1)

| Risk ID | Change | Old Assessment | New Assessment | Reason |
|---------|--------|---------------|----------------|--------|
| DRK-1 (SheetJS style parity) | **Reduced** | Medium/Medium | Low/Medium | D4 explicitly accepts limitations; known gaps documented; no longer a blocker |
| DRK-2 (OAuth scope creep) | **Reduced** | Low/Medium | Low/Low | D1 locks exact scope list; no ambiguity |
| DRK-8 (NEW) | **Added** | — | Medium/Low | Versioned import (D7) increases storage requirements — each refresh creates a new provenance record. Mitigated by metadata-only storage (file bytes not persisted server-side) |
| DRK-9 (NEW) | **Added** | — | Low/Low | Two-scope OAuth consent (D1) may confuse users seeing two permission dialogs. Mitigated by clear consent screen messaging |
| DRK-3 (Shared Drive permissions) | **Reduced** | Medium/Low | Low/Low | D3 locks hard-fail behavior; clear UX path |
| DRK-4 (Large files) | **Unchanged** | Low/Low | Low/Low | D5 sets 50MB cap |

---

## 5. Remaining Blockers

None. All 7 questions are locked with decisions. No external dependencies unresolved.

---

## 6. Cross-References

- `docs/features/V25_GOOGLE_DRIVE_INTEGRATION.md` — Feature specification
- `docs/handoff/V25_DRIVE_READINESS_REPORT.md` — Readiness assessment
- `docs/handoff/V25_DRIVE_TASK_LIST.md` — Implementation task list
- `docs/decisions/DECISION_V25_DRIVE_SCOPE.md` — Scope decisions
- `docs/api/API_SPEC_V2_5_CANONICAL.md` — Canonical API spec (Section 12)
- `docs/api/openapi.yaml` — OpenAPI 3.1 spec (Drive endpoints)

---

**Requesting APPROVE GATE 2**
