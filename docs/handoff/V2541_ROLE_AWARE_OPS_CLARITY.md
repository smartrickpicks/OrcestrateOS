# V2.54.1 — Role-Aware Operations View: Clarity Document

**Status:** Draft  
**Date:** 2026-02-17  
**Scope:** DOC + CLARITY ONLY — No code changes  
**Depends on:** V2.54 Operations View (migration 012, operations queue, feature flags)

---

## 1. Audit Snapshot

### 1.1 Frontend — Current Behavior

| Area | File/Line | Behavior | Issue |
|------|-----------|----------|-------|
| Feature flag load | `ui/viewer/index.html:39095-39103` | `_opsViewFlags` fetched once on page load from `GET /api/v2.5/feature-flags`. If `dbRead` is true, calls `opsDbHydrateQueue()` immediately. | Flags are fetched once and never re-fetched on role switch. |
| DB queue hydration | `ui/viewer/index.html:39106-39137` | `opsDbHydrateQueue()` calls `GET /workspaces/{ws}/operations/queue?limit=200`. Merges DB items into `verifierQueueState.payloads` by ID, marks them `_fromDb: true`. | No role filtering — all items returned regardless of sandbox role. No cache invalidation on role switch. |
| DB write (updatePayloadStatus) | `ui/viewer/index.html:39140-39155` | `opsDbWriteStatus()` sends `PATCH /api/v2.5/workspaces/{ws}/patches/{id}` | **URL MISMATCH**: Backend route is `PATCH /api/v2.5/patches/{id}` (no `/workspaces/{ws}/` prefix). Will 404 or hit wrong handler. |
| DB write (vrApprove) | `ui/viewer/index.html:44429-44430` | Calls `opsDbWriteStatus(vrState.currentPatchId, 'Verifier_Approved', version)` | Same URL mismatch. Version pulled from queue payload, correct pattern. |
| DB write (vrReject) | `ui/viewer/index.html:44453-44454` | Calls `opsDbWriteStatus(vrState.currentPatchId, 'Rejected', version)` | Same URL mismatch. |
| DB write gating | `ui/viewer/index.html:43242` | Only `payload.type === 'patch'` items trigger DB writes. RFIs/corrections skip DB write path. | Correct gating — but no DB write path exists for RFI/correction status changes. |
| Optimistic local update | `ui/viewer/index.html:43239-43249` | `payload.status = newStatus` is set BEFORE the async DB write returns. `saveVerifierQueue()` persists to localStorage immediately. | If DB write fails (409, 403, network), local state diverges from DB. No rollback. |
| Role switching | `ui/viewer/index.html:25577-25601` | `_roleSimulation` tracks `actualRole` and `effectiveRole`. `updateRoleSimBadges()` updates UI chrome. `applyRoleBasedModeRestrictions()` locks mode switcher. | **No re-hydration**: switching roles does not clear `verifierQueueState.payloads`, does not re-fetch from DB, does not invalidate localStorage cache. |
| Mode variable | `ui/viewer/index.html:6779` | `currentMode` is set by `setMode()` and stored in `localStorage('viewer_mode_v10')`. | Used for UI gating but not sent as a header to DB endpoints. |

### 1.2 Backend — Current Behavior

| Area | File/Line | Behavior | Issue |
|------|-----------|----------|-------|
| Operations queue | `server/routes/operations_queue.py:154-230` | `GET /workspaces/{ws}/operations/queue` — uses `AuthClass.EITHER`, no `require_role()` call. Returns all patches + RFIs + corrections for workspace. | No role-based filtering. No role enforcement. Sandbox user gets full view regardless of simulated role. |
| Patch update | `server/routes/patches.py:278-340` | `PATCH /patches/{pat_id}` — uses `AuthClass.BEARER`. Checks `TRANSITION_MATRIX` for role-based transitions, enforces `author_only`, `self_approval_check`, OCC version. | Route prefix is `/api/v2.5/patches/{id}` — frontend sends to `/api/v2.5/workspaces/{ws}/patches/{id}` which does not exist. |
| Patch list | `server/routes/patches.py:89-164` | `GET /workspaces/{ws}/patches` — supports `record_id`, `batch_id` filters. | No role-based visibility filtering. |
| RFI update | `server/routes/rfis.py:283` | `PATCH /rfis/{rfi_id}` — uses `AuthClass.BEARER`. | No role-based transition matrix like patches have. |
| Correction update | `server/routes/corrections.py:202` | `PATCH /corrections/{cor_id}` | No role-based transition matrix. |
| Batch creation | `server/routes/batches.py:93-140` | `POST /workspaces/{ws}/batches` — accepts `name`, `source` (upload/merge/import), `batch_fingerprint`, `metadata`. | No `drive` source type. No drive file deduplication. No `drive_file_id` or revision tracking. |
| Feature flags | `server/feature_flags.py:61-68` | `OPS_VIEW_DB_READ` and `OPS_VIEW_DB_WRITE` — simple env-var booleans. | No per-workspace or per-role flag scoping. |

---

## 2. Sandbox Role-Switch Contract

### 2.1 Event Model

```
ROLE_SWITCH_EVENT {
  trigger:        User clicks role tab in sandbox mode selector
  source:         ui/viewer/index.html — applyRoleBasedModeRestrictions()
  previous_role:  _roleSimulation.effectiveRole (before)
  new_role:       _roleSimulation.effectiveRole (after)
  timestamp:      ISO-8601
}
```

### 2.2 Re-Hydration Trigger

On `ROLE_SWITCH_EVENT`:

1. **Clear role-cached queue state**:
   - `verifierQueueState.payloads = []`
   - `localStorage.removeItem('srr_verifier_queue_v1')`
   - Reset filter state: `verifierFilterState = { division: '', status: '', patchType: '' }`

2. **Re-fetch from DB annotation layer** (if `OPS_VIEW_DB_READ` is true):
   - Call `opsDbHydrateQueue()` with role-aware query param: `?role={effectiveRole}`
   - Backend filters items by role visibility rules (see Section 3)

3. **Fallback if DB read disabled**:
   - Call `reloadVerifierQueuesFromStore()` — existing localStorage + PATCH_REQUEST_STORE + ArtifactStore merge
   - Apply client-side role visibility filter before rendering

4. **Re-render**:
   - Call `renderVerifierTriage()`
   - Update tab counts

### 2.3 Cache Invalidation Rules

| Cache Layer | Invalidation Action |
|-------------|-------------------|
| `verifierQueueState.payloads` | Clear to `[]` |
| `localStorage('srr_verifier_queue_v1')` | Remove key |
| `verifierFilterState` | Reset to defaults |
| `localStorage('verifier_filter_*')` | Remove keys |
| Feature flags (`_opsViewFlags`) | No invalidation needed (flags are role-independent) |

### 2.4 Sandbox vs Production Parity

In sandbox mode, role simulation MUST emulate production visibility:
- Analyst sees only their own submitted patches/RFIs
- Verifier sees all workspace-scoped analyst submissions awaiting review
- Admin sees Verifier_Approved items + admin-hold items + full audit trail

The sandbox user identity remains `sandbox_user` but the `effectiveRole` header determines visibility.

---

## 3. Role Visibility Matrix

### 3.1 Patches

| Status | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| Draft | Own only | Hidden | All |
| Submitted | Own only | All (queue) | All |
| Needs_Clarification | Own only (action: respond) | All (action: re-review) | All |
| Verifier_Responded | Own only | All (action: approve/reject) | All |
| Verifier_Approved | Own only (read) | All (read) | All (action: approve/hold) |
| Admin_Hold | Hidden | Read only | All (action: approve/reject) |
| Admin_Approved | Read only | Read only | All (action: apply/send_to_kiwi) |
| Applied | Read only | Read only | All |
| Rejected | Own only | All (read) | All |
| Cancelled | Own only | Hidden | All |
| Sent_to_Kiwi | Hidden | Hidden | All |
| Kiwi_Returned | Hidden | Hidden | All |

### 3.2 RFIs

| Custody Status | Analyst | Verifier | Admin |
|----------------|---------|----------|-------|
| open | Own authored (action: respond) | All (read) | All |
| awaiting_verifier | Read only | All (action: review/return) | All |
| returned_to_analyst | Own authored (action: respond) | All (read) | All |
| resolved | Own authored (read) | All (read) | All |
| dismissed | Own authored (read) | All (read) | All |

### 3.3 Corrections

| Status | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| pending_verifier | Own authored | All (action: approve/reject) | All |
| approved | Read only | Read only | All |
| rejected | Own authored (read) | Read only | All |
| auto_applied | Read only | Read only | All |

### 3.4 Allowed Actions by Role

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| Create patch | Yes | No | Yes |
| Submit patch | Yes (own) | No | No |
| Request clarification | No | Yes | Yes |
| Approve patch (verifier) | No | Yes (not own) | No |
| Reject patch | No | Yes | Yes |
| Admin approve | No | No | Yes (not own) |
| Admin hold | No | No | Yes |
| Create RFI | Yes | Yes | Yes |
| Respond to RFI | Yes (own/assigned) | Yes | Yes |
| Create correction | Yes | Yes | Yes |
| Approve correction | No | Yes | Yes |

---

## 4. Endpoint Contract

### 4.1 Active Routes

| Method | Route | Auth | Role Check | OCC | Notes |
|--------|-------|------|-----------|-----|-------|
| GET | `/api/v2.5/workspaces/{ws}/operations/queue` | EITHER | **MISSING** — must add `require_role(ws, auth, "analyst")` + role-scoped filtering | N/A | Composite feed |
| GET | `/api/v2.5/workspaces/{ws}/patches` | EITHER | None — add role-scoped visibility | N/A | List |
| POST | `/api/v2.5/workspaces/{ws}/patches` | EITHER | None | N/A | Create |
| PATCH | `/api/v2.5/patches/{pat_id}` | BEARER | TRANSITION_MATRIX enforces role + author + self-approval | Version required | Update status |
| GET | `/api/v2.5/workspaces/{ws}/rfis` | EITHER | None — add role-scoped visibility | N/A | List |
| POST | `/api/v2.5/workspaces/{ws}/rfis` | EITHER | None | N/A | Create |
| PATCH | `/api/v2.5/rfis/{rfi_id}` | BEARER | Minimal | Version required | Update |
| GET | `/api/v2.5/workspaces/{ws}/corrections` | EITHER | None — add role-scoped visibility | N/A | List |
| PATCH | `/api/v2.5/corrections/{cor_id}` | EITHER | Minimal | Version required | Update |
| GET | `/api/v2.5/feature-flags` | None | None | N/A | Public |

### 4.2 Required Headers

| Header | Purpose | Required |
|--------|---------|----------|
| `Authorization: Bearer {token}` | Authentication | Yes (except feature-flags) |
| `X-Sandbox-Mode: true` | Sandbox bypass (dev only) | Optional |
| `Content-Type: application/json` | Request body format | Yes (for POST/PATCH) |

### 4.3 OCC / Versioning Rules

- All PATCH endpoints require `version` (integer) in request body
- Server compares `version` against current DB `version` column
- Mismatch returns `409 STALE_VERSION` with `current_version` in details
- On success, server increments version to `version + 1`
- Client must update local `db_version` on success to stay in sync

### 4.4 Mismatch Register

| ID | Description | Frontend | Backend | Fix |
|----|-------------|----------|---------|-----|
| MM-01 | **DB write URL mismatch** | `PATCH /api/v2.5/workspaces/{ws}/patches/{id}` (`ui/viewer/index.html:39144`) | `PATCH /api/v2.5/patches/{id}` (`server/routes/patches.py:278`) | Fix frontend URL to drop `/workspaces/{ws}/` prefix |
| MM-02 | **No RFI DB write path** | `opsDbWriteStatus` skips non-patch items | `PATCH /rfis/{id}` exists but not called from UI | Add `opsDbWriteRfiStatus()` for RFI custody transitions |
| MM-03 | **No correction DB write path** | `opsDbWriteStatus` skips non-patch items | `PATCH /corrections/{id}` exists but not called from UI | Add `opsDbWriteCorrectionStatus()` for correction approvals |
| MM-04 | **Optimistic local divergence** | Local status updated before DB write completes | DB write may fail (409/403/network) | Move local update into `.then(ok => { if (ok) ... })` callback |
| MM-05 | **Operations queue lacks role enforcement** | Sends no role header | `operations_queue.py` has no `require_role()` call | Add role check + role-filtered SQL |
| MM-06 | **Role switch does not re-hydrate** | `applyRoleBasedModeRestrictions()` does not clear/re-fetch queue | N/A (frontend-only) | Add `opsOnRoleSwitch()` hook |

---

## 5. Batch Identity Contract

### 5.1 Upload Batch Creation Rules

1. Every Excel file upload creates a **new batch** via `POST /workspaces/{ws}/batches`
2. `source = "upload"`
3. `batch_fingerprint` is optional (SHA-256 of file contents if computed by client)
4. Re-uploading the same file creates a new batch (no dedup by fingerprint today)
5. Batch is immutable once created — documents are attached, never moved between batches

### 5.2 Drive Batch Creation + Dedupe Rules

1. `source = "drive"` must be added to `ALLOWED_SOURCES` in `server/routes/batches.py:17`
2. A new batch is created **only when** `drive_file_id + revision_marker` changes:
   - `revision_marker` = Google Drive `modifiedTime` or `revisionId` (whichever the Drive API provides)
   - On each drive pull, client sends `{ source: "drive", metadata: { drive_file_id, revision_marker } }`
   - Backend checks: `SELECT id FROM batches WHERE workspace_id = %s AND metadata->>'drive_file_id' = %s AND metadata->>'revision_marker' = %s AND deleted_at IS NULL`
   - If match found: return existing batch (no new creation)
   - If no match: create new batch
3. **Non-merge guarantee**: batches are never merged. Each batch retains its own `batch_id`. Cross-batch queries use workspace scope.

### 5.3 Database Schema (batches table — existing)

```sql
batches (
  id              VARCHAR PRIMARY KEY,  -- bat_{ulid}
  workspace_id    VARCHAR NOT NULL REFERENCES workspaces(id),
  name            VARCHAR NOT NULL,
  source          VARCHAR NOT NULL DEFAULT 'upload',  -- upload | merge | import | drive
  batch_fingerprint VARCHAR,
  metadata        JSONB DEFAULT '{}',  -- { drive_file_id, revision_marker, ... }
  created_at      TIMESTAMPTZ DEFAULT NOW(),
  updated_at      TIMESTAMPTZ DEFAULT NOW(),
  deleted_at      TIMESTAMPTZ
)
```

---

## 6. Source-of-Truth / Precedence Contract

### 6.1 Data Precedence (Highest to Lowest)

```
1. DB Annotation Layer (PostgreSQL)
   ├── patches table (lifecycle status, version, author)
   ├── rfis table (custody status, version, responder)
   ├── corrections table (status, version, decided_by)
   └── annotations table (evidence marks, anchors)

2. Workbook Snapshot (IndexedDB)
   ├── Grid cell values
   ├── Semantic signals
   └── Session state (column mappings, filters)

3. Drive Metadata (Google Drive API)
   ├── File revision marker
   ├── File modification time
   └── Folder structure

4. Local Cache (localStorage)
   ├── verifierQueueState (srr_verifier_queue_v1)
   ├── Filter preferences
   └── Role simulation state
```

### 6.2 Conflict Resolution Rules

| Conflict | Resolution |
|----------|-----------|
| DB vs localStorage queue status | DB wins. On re-hydration, DB items overwrite localStorage items with same ID. |
| DB vs workbook cell value | DB patch `after_value` is canonical for governed fields. Workbook reflects latest applied state. |
| Drive revision vs existing batch | If revision_marker matches, reuse batch. If changed, new batch. Never overwrite. |
| Concurrent OCC conflict | 409 STALE_VERSION. Client must re-fetch, re-read version, and retry. |

---

## 7. Acceptance Criteria

### 7.1 Role Switching

| ID | Criterion | Pass/Fail |
|----|-----------|-----------|
| AC-RS-01 | Switching from Analyst to Verifier in sandbox clears `verifierQueueState.payloads` and re-fetches from DB | |
| AC-RS-02 | After switch to Verifier, queue shows all workspace patches in Submitted/Needs_Clarification/Verifier_Responded status | |
| AC-RS-03 | After switch to Analyst, queue shows only own-authored patches | |
| AC-RS-04 | After switch to Admin, queue shows Verifier_Approved + Admin_Hold items | |
| AC-RS-05 | Role switch badge updates immediately | |
| AC-RS-06 | Filter state resets on role switch | |

### 7.2 Queue Filtering

| ID | Criterion | Pass/Fail |
|----|-----------|-----------|
| AC-QF-01 | `?item_type=patch` returns only patches | |
| AC-QF-02 | `?item_type=rfi` returns only RFIs | |
| AC-QF-03 | `?batch_id={id}` scopes results to that batch | |
| AC-QF-04 | `?queue_status=pending` returns items needing action | |
| AC-QF-05 | Tab counts (pending/clarification/admin/resolved) are accurate | |

### 7.3 DB Write Consistency

| ID | Criterion | Pass/Fail |
|----|-----------|-----------|
| AC-DW-01 | Patch approve (Verifier) writes `Verifier_Approved` to DB | |
| AC-DW-02 | Patch reject writes `Rejected` to DB | |
| AC-DW-03 | 409 STALE_VERSION shows toast and does NOT update local state | |
| AC-DW-04 | 403 SELF_APPROVAL_BLOCKED shows toast and does NOT update local state | |
| AC-DW-05 | Network failure does NOT update local state | |
| AC-DW-06 | RFI custody transition writes to DB (when DB write enabled) | |
| AC-DW-07 | Correction approval writes to DB (when DB write enabled) | |

### 7.4 Batch Creation Correctness

| ID | Criterion | Pass/Fail |
|----|-----------|-----------|
| AC-BC-01 | Upload creates new batch every time | |
| AC-BC-02 | Drive pull with same file_id + same revision reuses existing batch | |
| AC-BC-03 | Drive pull with same file_id + different revision creates new batch | |
| AC-BC-04 | Batches are never merged across ingest channels | |
| AC-BC-05 | Cross-batch operations queue returns items from all batches in workspace | |

---

## 8. QA Plan

### 8.1 Sandbox Role-Switch Matrix

| Test | Steps | Expected |
|------|-------|----------|
| QA-SR-01 | Load sandbox as Analyst. Submit 3 patches. Switch to Verifier. | Queue shows 3 pending patches. Own-authored items visible. |
| QA-SR-02 | As Verifier, approve 1 patch. Switch to Admin. | Queue shows 1 Verifier_Approved item in admin tab. |
| QA-SR-03 | Switch back to Analyst. | Queue shows own patches only. Approved patch shows read-only status. |
| QA-SR-04 | Switch roles 5 times rapidly. | No duplicate items. Counts remain consistent. No JS errors. |
| QA-SR-05 | Switch role with OPS_VIEW_DB_READ=false. | Falls back to localStorage queue. No DB fetch. |

### 8.2 Multi-Analyst Concurrency

| Test | Steps | Expected |
|------|-------|----------|
| QA-MA-01 | Analyst A submits patch. Analyst B views queue as Verifier. | B sees A's patch in pending. |
| QA-MA-02 | Analyst A submits patch. Analyst A tries to approve own patch as Verifier. | 403 SELF_APPROVAL_BLOCKED. Toast shown. Local state unchanged. |
| QA-MA-03 | Verifier B approves. Meanwhile Verifier C tries to approve same patch. | C gets 409 STALE_VERSION (B already bumped version). Toast shown. |

### 8.3 Cross-Workspace Isolation

| Test | Steps | Expected |
|------|-------|----------|
| QA-CW-01 | User has roles in WS-A and WS-B. View queue in WS-A. | Only WS-A items shown. Zero WS-B items. |
| QA-CW-02 | Attempt to PATCH a patch from WS-B while authenticated for WS-A. | 404 or 403. No cross-workspace mutation. |

### 8.4 Drive Re-Pull Dedupe Tests

| Test | Steps | Expected |
|------|-------|----------|
| QA-DR-01 | Pull Drive file (file_id=F1, rev=R1). | New batch created. |
| QA-DR-02 | Pull same Drive file again (file_id=F1, rev=R1). | Existing batch returned. No new batch. |
| QA-DR-03 | Edit Drive file. Pull again (file_id=F1, rev=R2). | New batch created. Old batch untouched. |
| QA-DR-04 | Pull different Drive file (file_id=F2, rev=R1). | New batch created (different file). |

---

## 9. Clarity Questions (Blocking Only)

> Locked decisions from the brief are NOT repeated here.

| ID | Question | Blocking? | Default if Unanswered |
|----|----------|-----------|----------------------|
| CQ-01 | Should the operations queue endpoint accept an `X-Effective-Role` header for sandbox role simulation, or should it derive role from the authenticated user's workspace role? | Yes | Derive from DB `user_workspace_roles` table; sandbox bypass uses `effectiveRole` from simulation state. |
| CQ-02 | For Drive batch dedup, should `revision_marker` use `modifiedTime` (ISO string) or `revisionId` (opaque string)? Drive API provides both. | No | Use `modifiedTime` — it is always available (revisionId requires extra API scope). |
| CQ-03 | Should the operations queue support server-side pagination via ULID cursor, or is client-side filtering on a 200-item fetch sufficient for v2.54.1? | No | Keep client-side filtering with 200-item limit for this pass. Add server cursor in v2.55. |
| CQ-04 | When `OPS_VIEW_DB_WRITE` is true but the DB write fails, should the UI block the local state update (strict mode) or warn and allow (permissive mode)? | Yes | Strict mode — do NOT update local state on DB write failure. Show error toast. |

---

## 10. Go/No-Go

### 10.1 Implementation Readiness

| Area | Ready? | Blocker |
|------|--------|---------|
| Migration 012 (batch_id on rfis) | Yes | Deployed and backfilled |
| Operations queue endpoint | Partial | Needs role enforcement (VER2-03) |
| Feature flags | Yes | Deployed |
| Frontend DB write | No | URL mismatch (MM-01) must be fixed first |
| Frontend role-switch re-hydration | No | Not implemented (VER2-01) |
| RFI/correction DB write path | No | Not implemented (MM-02, MM-03) |
| Optimistic update rollback | No | Not implemented (MM-04) |
| Drive batch dedup | No | `source = "drive"` not in ALLOWED_SOURCES, no dedup query |
| Batch identity rules | Partial | Upload works; Drive rules need implementation |

### 10.2 Verdict

**NO-GO for production.** Four P0 blockers must be resolved:

1. **MM-01**: Frontend DB write URL mismatch — all DB writes silently 404
2. **VER2-01**: Role-switch re-hydration — sandbox shows stale cross-role data
3. **MM-04**: Optimistic local divergence — UI shows success when DB write fails
4. **MM-05**: Operations queue lacks role enforcement — all roles see all data

### 10.3 Out-of-Scope (Next Phase)

- Admin God Mode (full cross-workspace visibility)
- Real-time WebSocket push for queue updates
- Offline-first conflict resolution
- Batch archival / soft-delete lifecycle

---

## 11. Task List

| Task ID | Priority | Description | Depends On |
|---------|----------|-------------|------------|
| VER2-01 | P0 | Sandbox role-switch: add `opsOnRoleSwitch()` hook — clear queue, re-fetch from DB, reset filters | — |
| VER2-02 | P0 | Fix frontend DB write URL: change `opsDbWriteStatus` from `/workspaces/{ws}/patches/{id}` to `/patches/{id}` | — |
| VER2-03 | P0 | Add `require_role()` to operations queue endpoint + role-scoped SQL filtering | — |
| VER2-04 | P0 | Fix optimistic local update: move `payload.status = newStatus` into `.then(ok => ...)` callback | VER2-02 |
| VER2-05 | P1 | Add `opsDbWriteRfiStatus()` — PATCH `/rfis/{id}` for custody transitions when DB write enabled | VER2-02 |
| VER2-06 | P1 | Add `opsDbWriteCorrectionStatus()` — PATCH `/corrections/{id}` for approval when DB write enabled | VER2-02 |
| VER2-07 | P1 | Add `X-Effective-Role` header support to operations queue for sandbox role simulation | VER2-03 |
| VER2-08 | P2 | Add `source = "drive"` to `ALLOWED_SOURCES` in batches route | — |
| VER2-09 | P2 | Implement Drive batch dedup: check `metadata->>'drive_file_id'` + `metadata->>'revision_marker'` before creating batch | VER2-08 |
| VER2-10 | P3 | Add role-scoped visibility filters to `GET /workspaces/{ws}/patches` and `GET /workspaces/{ws}/rfis` | VER2-03 |
| VER2-11 | P3 | Add RFI custody transition matrix (analogous to patch `TRANSITION_MATRIX`) | VER2-05 |
| VER2-12 | P4 | QA execution: run full sandbox role-switch matrix, concurrency, isolation, and drive dedup tests | VER2-01..VER2-09 |
