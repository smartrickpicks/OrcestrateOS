# V2.54 Verifier Annotation Layer — Doc Phase Audit

**Version:** 2.54  
**Date:** 2026-02-17  
**Status:** DOC PHASE — No code changes  
**Scope:** Verifier Dashboard annotation-layer-first architecture  

---

## 1. Audit Snapshot

### 1.1 Current Verifier Data Flow Map

The verifier dashboard currently operates on a **dual-source architecture** where the UI reads from localStorage/memory while the server maintains a parallel (but disconnected) DB layer.

#### DB-Backed (Server Canonical)

| Resource | Table | Route File | Key Endpoints | Workspace Isolated | Batch Scoped |
|----------|-------|-----------|---------------|-------------------|-------------|
| Patches | `patches` | `server/routes/patches.py` | `GET /workspaces/{ws}/patches`, `POST`, `PATCH /patches/{id}` | Yes (L106) | Column exists, no batch-scoped list endpoint |
| RFIs | `rfis` | `server/routes/rfis.py` | `GET /workspaces/{ws}/rfis`, `POST`, `PATCH /rfis/{id}`, `GET /batches/{bat}/rfis` | Yes (L91) | **Partially** — see Finding F3 |
| Corrections | `corrections` | `server/routes/corrections.py` | `POST /documents/{doc}/corrections`, `PATCH /corrections/{id}`, `GET /batches/{bat}/corrections` | Yes (L110) | Yes, via document→batch join (L399) |
| Anchors | `anchors` | `server/routes/anchors.py` | `POST /documents/{doc}/anchors`, `GET /documents/{doc}/anchors`, `DELETE /anchors/{id}` | Yes (L109) | Via document parent |
| Annotations | `annotations` | `server/routes/annotations.py` | `GET /workspaces/{ws}/annotations`, `POST`, `PATCH /annotations/{id}` | Yes (L50) | No batch filter |
| Batch Health | (computed) | `server/routes/batch_health.py` | `GET /batches/{bat}/health` | Yes (L37) | **Partially** — see Finding F3 |
| SSE Stream | `audit_events` | `server/routes/sse_stream.py` | `GET /workspaces/{ws}/events/stream` | Yes (L132) | No batch filter |

#### Local-Only (Client State — NOT DB-Backed)

| Store | Storage Mechanism | Location in `index.html` | Persistence |
|-------|------------------|-------------------------|-------------|
| `verifierQueueState` | `localStorage` key `srr_verifier_queue_v1` | L39092 | Per-browser, survives refresh |
| `PATCH_REQUEST_STORE` | `localStorage` keys with `pr:{env}:` prefix | L7403–7460 | Per-browser, per-environment |
| `ARTIFACT_STORE` | `localStorage` keys with `fs:{env}/{ws}/` prefix | L7288–7370 | Per-browser, per-environment, per-workspace |
| `verifierFilterState` | `localStorage` keys `verifier_filter_*` | L39098–39102 | Per-browser |
| `vrState` (review state) | In-memory only | L43795+ (via `vrApprove`/`vrReject`) | Lost on page refresh |
| `changeMapStore` | In-memory | (various) | Lost on page refresh |

#### Evidence of localStorage-Driven Verifier Queue

1. **Queue loading** (`reloadVerifierQueuesFromStore`, L39432–39545): Loads from `localStorage.getItem('srr_verifier_queue_v1')`, then merges `PATCH_REQUEST_STORE.list()` and `listArtifacts()` — all localStorage. **Never calls any `/api/v2.5/` endpoint.**

2. **Queue rendering** (`renderVerifierTriage`, L43072–43207): Reads directly from `verifierQueueState.payloads` (in-memory array backed by localStorage). **No DB fetch.**

3. **Verifier actions** (`vrApprove` L44331, `vrReject` L44359): Update `vrState` in memory, call `vrLogAuditEvent` which writes to `ARTIFACT_STORE` (localStorage). **No API call to PATCH /patches/{id} or PATCH /rfis/{id}.**

4. **Status transitions** (`updatePayloadStatus`, L43207+): Updates `verifierQueueState.payloads[].status` in memory, calls `saveVerifierQueue()` → `localStorage.setItem(...)`. Also writes to `ARTIFACT_STORE`. **Never calls server.**

5. **Payload creation** (L33137–33185): Creates verifier payloads from imported RFI sheets, pushes to `verifierQueueState.payloads`, calls `saveVerifierQueue()`. **No DB write.**

### 1.2 Findings

**F1: Verifier queue is 100% localStorage-driven.**  
`verifierQueueState` (L39092) initializes from `localStorage.getItem('srr_verifier_queue_v1')`. `reloadVerifierQueuesFromStore()` (L39432) merges from `PATCH_REQUEST_STORE` and `ARTIFACT_STORE` — both localStorage. `saveVerifierQueue()` (L39546) writes back to localStorage. The DB is never consulted.

**F2: vrApprove/vrReject never persist to DB.**  
`vrApprove()` (L44331) sets `vrState.reviewState = 'Verifier_Approved'` and calls `vrLogAuditEvent()` which writes to `ARTIFACT_STORE.fsAppend('events.jsonl', ...)` — localStorage. The server's `PATCH /patches/{pat_id}` endpoint with its full transition matrix (L26–49 of `patches.py`) is never invoked.

**F3: Batch-level RFI filtering is workspace-wide, not batch-scoped.**  
`list_batch_rfis` (rfis.py L500–501) filters by `workspace_id` extracted from the batch, but does NOT join RFIs to the batch through records/documents. It returns ALL workspace RFIs matching the status filter, not just those belonging to the batch's records. Similarly, `batch_health.py` L40–51 counts RFIs by `workspace_id`, not `batch_id`.

**F4: No record-scoped patch or correction list endpoints.**  
`list_patches` (patches.py L89) filters by workspace + optional `status` and `author_id`, but has no `record_id` filter parameter. The UI needs to show all patches for a specific record in the verifier review detail, but must fetch all workspace patches and filter client-side.

**F5: Annotations endpoint has no target_type filter.**  
`list_annotations` (annotations.py L36) lists by workspace with cursor pagination, but offers no `target_type` or `target_id` filter. Cannot efficiently query "all annotations on patch X" or "all annotations on record Y".

**F6: SSE stream has no resource-type filter.**  
`sse_event_stream` (sse_stream.py L120) emits all audit events for the workspace. A verifier watching a specific batch or record gets flooded with unrelated events.

**F7: Corrections endpoint lacks workspace-level list.**  
Corrections can only be listed by document (`/documents/{doc}/corrections` — not implemented as GET) or by batch (`/batches/{bat}/corrections`). No `/workspaces/{ws}/corrections` endpoint exists.

**F8: Dual-write gap.**  
Per `DECISION_V25_DB.md`, the architecture mandates a "dual-write period: client writes locally AND to server; server is source of truth." This dual-write is not implemented for verifier actions. Writes go to localStorage only.

---

## 2. Source-of-Truth Contract

### 2.1 Final Precedence Policy

| Layer | Priority | Description | Conflict Behavior |
|-------|----------|-------------|-------------------|
| **DB Annotation Layer** | **P0 — Canonical** | `patches`, `rfis`, `corrections`, `anchors`, `annotations` tables | Always wins. Server is authoritative. |
| **Imported Workbook Baseline** | P1 — Reference | Row/field data from CSV/XLSX import stored in `batches` + `records` | Read-only after import. Provides baseline values for change detection. |
| **Drive Source Metadata** | P2 — Context | Google Drive file metadata, folder routing, export history | Informational. Never overrides annotation layer decisions. |
| **Client localStorage** | P3 — Cache/Offline | `verifierQueueState`, `PATCH_REQUEST_STORE`, `ARTIFACT_STORE` | **Must be treated as expendable cache.** Server state always wins on reconnect. |

### 2.2 Conflict Resolution Rules

1. **DB vs. localStorage divergence:** DB wins. On page load, the verifier queue MUST be hydrated from DB, not localStorage. localStorage may serve as optimistic cache during network failures only.

2. **Patch status conflicts:** Server's `patches.version` column with optimistic concurrency (409 STALE_VERSION) is the arbiter. Client must retry with fresh version.

3. **RFI custody conflicts:** Server's `rfis.custody_status` + `custody_owner_id` is canonical. The custody transition matrix in `rfis.py` (L20–26) is the single source of allowed transitions.

4. **Correction status conflicts:** Server's `corrections.status` with the transition matrix in `corrections.py` (L30–35) governs allowed state changes. Verifier role check (L280–291) is server-enforced.

5. **Offline-first degradation:** If the server is unreachable, the UI MAY display locally cached data with a clear "offline / unsynced" indicator. No governance decisions (approve, reject, transition) are valid without server confirmation.

### 2.3 Key Invariant

> **If the source document is unavailable, the verifier MUST still function from DB annotation state.**

This means: the verifier review page must load patch details, RFI history, correction proposals, and anchor references entirely from the annotation layer endpoints — never requiring the original PDF/XLSX to be fetchable.

---

## 3. Endpoint Plan

### 3.1 Existing Endpoints to Reuse (No Changes)

| Endpoint | Method | Purpose | Verifier Use Case |
|----------|--------|---------|-------------------|
| `GET /workspaces/{ws}/patches` | GET | List patches | Load verifier queue (patches in `Submitted`/`Verifier_Responded` status) |
| `GET /patches/{pat_id}` | GET | Get single patch | Verifier review detail |
| `PATCH /patches/{pat_id}` | PATCH | Status transition | `vrApprove` → status=`Verifier_Approved`, `vrReject` → status=`Rejected` |
| `GET /workspaces/{ws}/rfis` | GET | List RFIs | RFI queue items |
| `GET /rfis/{rfi_id}` | GET | Get single RFI | RFI detail in review |
| `PATCH /rfis/{rfi_id}` | PATCH | Custody transition | Verifier responds/resolves/dismisses |
| `POST /documents/{doc}/corrections` | POST | Create correction | Verifier-initiated corrections |
| `PATCH /corrections/{cor_id}` | PATCH | Approve/reject correction | Correction review actions |
| `GET /documents/{doc}/anchors` | GET | List anchors | Evidence anchors for review |
| `GET /workspaces/{ws}/events/stream` | SSE | Real-time events | Live queue updates |
| `GET /batches/{bat}/health` | GET | Batch health summary | Dashboard header counts |

### 3.2 Missing Endpoints to Add (Additive Only)

#### EP-01: `GET /workspaces/{ws}/patches` — Add `record_id` and `batch_id` query params

- **Method:** GET (existing endpoint, additive filter params)
- **Path:** `/api/v2.5/workspaces/{ws_id}/patches`
- **New Query Params:** `record_id` (string, optional), `batch_id` (string, optional)
- **Request:** `GET /api/v2.5/workspaces/ws_SEED.../patches?record_id=rec_abc&status=Submitted`
- **Response Envelope:** Existing `collection_envelope` — no change
- **RBAC:** Existing `require_auth(AuthClass.EITHER)` — no change
- **Audit Event:** None (read-only)
- **Implementation:** Add `record_id` and `batch_id` filter conditions to `list_patches` (patches.py L89–149)

#### EP-02: `GET /workspaces/{ws}/rfis` — Add `batch_id` query param

- **Method:** GET (existing endpoint, additive filter param)
- **Path:** `/api/v2.5/workspaces/{ws_id}/rfis`
- **New Query Params:** `batch_id` (string, optional) — joins through `patches.batch_id` or via `metadata->>'batch_id'`
- **Request:** `GET /api/v2.5/workspaces/ws_SEED.../rfis?batch_id=bat_xyz`
- **Response Envelope:** Existing `collection_envelope` — no change
- **RBAC:** Existing `require_auth(AuthClass.EITHER)` — no change
- **Audit Event:** None (read-only)
- **Implementation:** Add `batch_id` subquery join to `list_rfis` (rfis.py L76–130)

#### EP-03: `GET /batches/{bat_id}/rfis` — Fix batch-scoping

- **Method:** GET (existing endpoint, **fix** to scope correctly)
- **Path:** `/api/v2.5/batches/{bat_id}/rfis`
- **Current Bug:** Filters by `workspace_id` from batch, returns ALL workspace RFIs (rfis.py L500–501)
- **Fix:** Add `target_record_id IN (SELECT record_id FROM patches WHERE batch_id = %s)` condition, OR add a `batch_id` column to `rfis` table (additive migration)
- **Response Envelope:** Existing `collection_envelope` — no change
- **RBAC:** Existing — no change
- **Audit Event:** None (read-only)

#### EP-04: `GET /workspaces/{ws}/corrections`

- **Method:** GET (new endpoint)
- **Path:** `/api/v2.5/workspaces/{ws_id}/corrections`
- **Query Params:** `status` (string, optional), `cursor` (string, optional), `limit` (int, optional, default 50), `batch_id` (string, optional)
- **Request:** `GET /api/v2.5/workspaces/ws_SEED.../corrections?status=pending_verifier`
- **Response Envelope:**
  ```json
  {
    "data": [...],
    "meta": { "cursor": "...", "has_more": false, "limit": 50 }
  }
  ```
- **RBAC:** `require_auth(AuthClass.EITHER)` + workspace membership
- **Audit Event:** None (read-only)
- **Implementation:** New handler in `corrections.py`

#### EP-05: `GET /workspaces/{ws}/annotations` — Add `target_type` and `target_id` filters

- **Method:** GET (existing endpoint, additive filter params)
- **Path:** `/api/v2.5/workspaces/{ws_id}/annotations`
- **New Query Params:** `target_type` (string, optional), `target_id` (string, optional)
- **Request:** `GET /api/v2.5/workspaces/ws_SEED.../annotations?target_type=patch&target_id=pat_abc`
- **Response Envelope:** Existing `collection_envelope` — no change
- **RBAC:** Existing — no change
- **Audit Event:** None (read-only)

#### EP-06: `GET /workspaces/{ws}/verifier/queue`

- **Method:** GET (new composite endpoint)
- **Path:** `/api/v2.5/workspaces/{ws_id}/verifier/queue`
- **Query Params:** `batch_id` (string, optional), `queue_tab` (string, optional: `pending|needs_clarification|sent_to_admin|resolved`), `cursor`, `limit`
- **Request:** `GET /api/v2.5/workspaces/ws_SEED.../verifier/queue?queue_tab=pending&batch_id=bat_xyz`
- **Response Envelope:**
  ```json
  {
    "data": {
      "items": [
        {
          "id": "pat_abc | rfi_xyz | cor_123",
          "item_type": "patch | rfi | correction",
          "record_id": "rec_...",
          "field_key": "label_vendor",
          "status": "Submitted",
          "custody_owner_role": "verifier",
          "author_id": "usr_...",
          "created_at": "2026-02-17T...",
          "summary": "...",
          "batch_id": "bat_...",
          "metadata": {}
        }
      ],
      "counts": {
        "pending": 12,
        "needs_clarification": 3,
        "sent_to_admin": 5,
        "resolved": 8
      }
    },
    "meta": { "cursor": "...", "has_more": false, "limit": 50 }
  }
  ```
- **RBAC:** `require_auth(AuthClass.BEARER)` + role >= `verifier`
- **Audit Event:** None (read-only)
- **Implementation:** New route file `server/routes/verifier_queue.py`. Queries `patches` (status in verifier-actionable states), `rfis` (custody_status = `awaiting_verifier`), and `corrections` (status = `pending_verifier`), merges into unified shape, sorts by created_at DESC.

#### EP-07: `GET /batches/{bat_id}/health` — Fix RFI batch-scoping

- **Method:** GET (existing endpoint, **fix** to scope correctly)
- **Path:** `/api/v2.5/batches/{bat_id}/health`
- **Current Bug:** RFI counts use `workspace_id` filter (batch_health.py L40–51), returning workspace-wide counts instead of batch-scoped
- **Fix:** Join RFIs to batch through `patches.batch_id` or add `batch_id` to rfis
- **Response Envelope:** Existing — no change
- **RBAC:** Existing — no change

### 3.3 Normalized Verifier Queue Item Shape

All queue items (patches, RFIs, corrections) are normalized to a unified shape for the UI:

```typescript
interface VerifierQueueItem {
  id: string;                    // pat_*, rfi_*, cor_*
  item_type: 'patch' | 'rfi' | 'correction';
  record_id: string | null;
  field_key: string | null;
  batch_id: string | null;
  status: string;                // Lifecycle-specific status
  queue_status: string;          // Normalized: pending|needs_clarification|sent_to_admin|resolved
  custody_owner_role: string | null;  // analyst|verifier|admin|null
  author_id: string;
  created_at: string;            // ISO timestamp
  summary: string;               // Human-readable summary
  before_value: string | null;
  after_value: string | null;
  version: number;
  metadata: object;
}
```

**Queue status mapping:**

| Resource | Source Status | Queue Status |
|----------|-------------|-------------|
| Patch | `Submitted` | `pending` |
| Patch | `Needs_Clarification` | `needs_clarification` |
| Patch | `Verifier_Approved` | `sent_to_admin` |
| Patch | `Applied`/`Rejected`/`Cancelled` | `resolved` |
| RFI | `awaiting_verifier` | `pending` |
| RFI | `returned_to_analyst` | `needs_clarification` |
| RFI | `resolved`/`dismissed` | `resolved` |
| Correction | `pending_verifier` | `pending` |
| Correction | `approved`/`rejected` | `resolved` |

---

## 4. Task List

### DOC Tasks

| ID | Priority | Type | Description |
|----|----------|------|-------------|
| VER-01 | P0 | DOC | Lock this source-of-truth contract (Section 2) as a decision doc in `docs/decisions/DECISION_VERIFIER_ANNOTATION_LAYER.md` |
| VER-02 | P0 | DOC | Document the normalized queue item shape (Section 3.3) in `docs/api/API_SPEC_V2_5_CANONICAL.md` addendum |
| VER-03 | P1 | DOC | Add EP-06 (`/verifier/queue`) to `docs/api/openapi.yaml` |

### CLARITY Tasks

| ID | Priority | Type | Description |
|----|----------|------|-------------|
| VER-04 | P0 | CLARITY | Decide: Add `batch_id` column to `rfis` table (additive migration) vs. join through `patches.batch_id`? See Clarity Q1. |
| VER-05 | P1 | CLARITY | Decide: Should corrections be linkable to batches directly (add `batch_id` column) or continue via `documents.batch_id` join? See Clarity Q2. |
| VER-06 | P1 | CLARITY | Decide: localStorage retention strategy during migration. See Clarity Q3. |

### IMPLEMENT Tasks

| ID | Priority | Type | Description | Depends On |
|----|----------|------|-------------|------------|
| VER-10 | P0 | IMPLEMENT | Add `record_id` and `batch_id` filter params to `GET /workspaces/{ws}/patches` (EP-01) | — |
| VER-11 | P0 | IMPLEMENT | Fix `GET /batches/{bat}/rfis` batch-scoping bug (EP-03) | VER-04 |
| VER-12 | P0 | IMPLEMENT | Fix `GET /batches/{bat}/health` RFI batch-scoping bug (EP-07) | VER-04 |
| VER-13 | P0 | IMPLEMENT | Add `batch_id` filter param to `GET /workspaces/{ws}/rfis` (EP-02) | VER-04 |
| VER-14 | P1 | IMPLEMENT | Add `GET /workspaces/{ws}/corrections` workspace-level list endpoint (EP-04) | — |
| VER-15 | P1 | IMPLEMENT | Add `target_type`/`target_id` filter params to `GET /workspaces/{ws}/annotations` (EP-05) | — |
| VER-16 | P1 | IMPLEMENT | Create `GET /workspaces/{ws}/verifier/queue` composite endpoint (EP-06) | VER-10, VER-11, VER-13, VER-14 |
| VER-17 | P2 | IMPLEMENT | Wire `vrApprove()` to call `PATCH /patches/{pat_id}` with status transition + version | VER-10 |
| VER-18 | P2 | IMPLEMENT | Wire `vrReject()` to call `PATCH /patches/{pat_id}` with status=`Rejected` + version | VER-10 |
| VER-19 | P2 | IMPLEMENT | Wire `renderVerifierTriage()` to hydrate from `GET /verifier/queue` instead of localStorage | VER-16 |
| VER-20 | P2 | IMPLEMENT | Wire RFI custody transitions in verifier UI to call `PATCH /rfis/{rfi_id}` | — |
| VER-21 | P2 | IMPLEMENT | Wire correction approve/reject in verifier UI to call `PATCH /corrections/{cor_id}` | — |
| VER-22 | P3 | IMPLEMENT | Add batch-scoped SSE filter param to `/events/stream` (optional `batch_id`, `resource_type` query params) | — |
| VER-23 | P3 | IMPLEMENT | Implement localStorage-to-DB migration utility for existing verifier queue data | VER-16 |
| VER-24 | P4 | IMPLEMENT | Remove legacy localStorage verifier queue code after migration period | VER-23 |

### AUDIT/TEST Tasks

| ID | Priority | Type | Description | Depends On |
|----|----------|------|-------------|------------|
| VER-30 | P0 | AUDIT | Verify no self-approval bypass: server enforces `self_approval_check` (patches.py L363), confirm UI cannot circumvent | VER-17 |
| VER-31 | P1 | AUDIT | Verify workspace isolation: all new/modified endpoints reject cross-workspace access | VER-10–VER-16 |
| VER-32 | P1 | AUDIT | Verify optimistic concurrency: all PATCH endpoints check version, return 409 on stale | VER-17–VER-21 |
| VER-33 | P2 | TEST | Integration test: verifier approves patch → DB status = `Verifier_Approved` → SSE event emitted | VER-17 |
| VER-34 | P2 | TEST | Integration test: verifier rejects patch → DB status = `Rejected` → audit event logged | VER-18 |
| VER-35 | P2 | TEST | Integration test: RFI custody transition `awaiting_verifier` → `resolved` with role check | VER-20 |
| VER-36 | P2 | TEST | Integration test: correction `pending_verifier` → `approved` with role check | VER-21 |

---

## 5. Acceptance Criteria

### P0 Criteria (Must Pass for Go)

| AC-ID | Task | Criterion | Pass/Fail |
|-------|------|-----------|-----------|
| AC-01 | VER-10 | `GET /workspaces/{ws}/patches?record_id=rec_X` returns only patches for that record | |
| AC-02 | VER-10 | `GET /workspaces/{ws}/patches?batch_id=bat_X` returns only patches in that batch | |
| AC-03 | VER-11 | `GET /batches/{bat}/rfis` returns only RFIs linked to records in that batch, NOT all workspace RFIs | |
| AC-04 | VER-12 | `GET /batches/{bat}/health` RFI counts reflect only the target batch, NOT the entire workspace | |
| AC-05 | VER-17 | `vrApprove()` calls `PATCH /patches/{id}` with `{status: "Verifier_Approved", version: N}` and handles 409 | |
| AC-06 | VER-18 | `vrReject()` calls `PATCH /patches/{id}` with `{status: "Rejected", version: N}` and handles 409 | |
| AC-07 | VER-30 | Self-approval blocked: verifier who authored a patch cannot approve it (server returns 403 `SELF_APPROVAL_BLOCKED`) | |
| AC-08 | VER-01 | Source-of-truth contract is locked as a decision doc | |

### P1 Criteria

| AC-ID | Task | Criterion | Pass/Fail |
|-------|------|-----------|-----------|
| AC-10 | VER-14 | `GET /workspaces/{ws}/corrections?status=pending_verifier` returns workspace corrections filtered by status | |
| AC-11 | VER-15 | `GET /workspaces/{ws}/annotations?target_type=patch&target_id=pat_X` returns only matching annotations | |
| AC-12 | VER-16 | `GET /workspaces/{ws}/verifier/queue?queue_tab=pending` returns unified list of patches + RFIs + corrections awaiting verifier action | |
| AC-13 | VER-31 | All new/modified endpoints reject requests where user has no role in the target workspace (403 or 404) | |

### P2 Criteria

| AC-ID | Task | Criterion | Pass/Fail |
|-------|------|-----------|-----------|
| AC-20 | VER-19 | `renderVerifierTriage()` loads data from `GET /verifier/queue` on page load, not from localStorage | |
| AC-21 | VER-20 | RFI custody transition in UI calls `PATCH /rfis/{id}` and updates queue on success | |
| AC-22 | VER-21 | Correction approval in UI calls `PATCH /corrections/{id}` and updates queue on success | |
| AC-23 | VER-32 | Stale version (409) during approval shows user-friendly "someone else modified this" message and refreshes | |

---

## 6. QA/Test Plan

### 6.1 Smoke Steps

| Step | Action | Expected Result |
|------|--------|-----------------|
| S1 | Load verifier dashboard as `verifier` role | Queue loads from DB endpoint, not localStorage |
| S2 | Open a pending patch in review detail | Patch data rendered from `GET /patches/{id}` |
| S3 | Click "Approve" on a patch authored by someone else | `PATCH /patches/{id}` called with `Verifier_Approved`, toast confirms, queue refreshes |
| S4 | Click "Approve" on a patch you authored | Self-approval blocked, error toast, no state change |
| S5 | Click "Reject" without notes | Warning: "add rejection reason" |
| S6 | Click "Reject" with notes | `PATCH /patches/{id}` called with `Rejected`, toast confirms |
| S7 | Respond to RFI in `awaiting_verifier` state | `PATCH /rfis/{id}` with `custody_status=resolved`, custody transferred |
| S8 | Approve a `pending_verifier` correction | `PATCH /corrections/{id}` with `status=approved`, decided_by set |
| S9 | Filter queue by `batch_id` | Only items from that batch appear |
| S10 | Reload page after verifier actions | Queue state matches DB (not stale localStorage) |

### 6.2 Role-Based Permission Checks

| Test | Actor Role | Action | Expected |
|------|-----------|--------|----------|
| R1 | `analyst` | Attempt `PATCH /patches/{id}` with status=`Verifier_Approved` | 403 Forbidden |
| R2 | `verifier` | Approve own patch | 403 `SELF_APPROVAL_BLOCKED` |
| R3 | `verifier` | Approve another's patch | 200 OK |
| R4 | `analyst` | Attempt RFI custody transition `awaiting_verifier` → `resolved` | 403 `ROLE_NOT_ALLOWED` |
| R5 | `verifier` | RFI custody transition `awaiting_verifier` → `resolved` | 200 OK |
| R6 | `analyst` | Attempt correction approval | 403 `ROLE_NOT_ALLOWED` |
| R7 | `admin` | All verifier actions | 200 OK (admin inherits verifier permissions) |
| R8 | No workspace role | Any endpoint | 403 or 404 |

### 6.3 Concurrency Checks

| Test | Scenario | Expected |
|------|----------|----------|
| C1 | Two verifiers load same patch simultaneously; first approves, second approves | Second gets 409 `STALE_VERSION`, must refresh |
| C2 | Verifier loads patch at version 3; analyst updates metadata (version 4); verifier approves with version 3 | 409 `STALE_VERSION` |
| C3 | RFI custody transition with stale version | 409 `STALE_VERSION` |

### 6.4 Workspace Isolation Checks

| Test | Scenario | Expected |
|------|----------|----------|
| W1 | Verifier in ws_A calls `GET /workspaces/ws_B/verifier/queue` | 403 or 404 (no role in ws_B) |
| W2 | Verifier in ws_A calls `PATCH /patches/{pat_in_ws_B}` | 403 (role check fails) |
| W3 | Batch health for batch in ws_A queried by user with no ws_A role | 404 |

---

## 7. Clarity Questions

### Q1: RFI Batch-Scoping Strategy (BLOCKER — Required for VER-04, VER-11, VER-12, VER-13)

**Question:** Should we add a `batch_id` column to the `rfis` table (additive migration 012), or scope RFIs to batches via JOIN through `patches.batch_id`?

**Options:**

| Option | Pros | Cons |
|--------|------|------|
| A: Add `batch_id` to `rfis` | Simple queries, direct filter, fast | Denormalization; must keep in sync if RFI moves across batches |
| B: JOIN via `patches.batch_id` | No schema change needed | Not all RFIs have a `patch_id`; standalone RFIs would be unscoped |
| C: Use `target_record_id` → `records.batch_id` JOIN | True relational scoping | Requires `records` table to exist (currently records are client-side sheet rows, NOT in DB) |

**Recommendation:** **Option A** — add `batch_id` column to `rfis` (nullable, additive migration). This is the simplest path that preserves backward compatibility. Populate from the batch context at RFI creation time. Standalone RFIs (no batch context) have NULL `batch_id` and appear in workspace-level queries only.

### Q2: Correction Batch Linkage

**Question:** Should corrections gain a direct `batch_id` column, or continue relying on `document_id → documents.batch_id` JOIN?

**Recommendation:** Keep the current JOIN approach. Corrections are always created via `/documents/{doc}/corrections` which already provides the document→batch chain. Adding `batch_id` would be redundant denormalization with low value. The `GET /batches/{bat}/corrections` endpoint already works correctly via this JOIN (corrections.py L398–399).

### Q3: localStorage Migration Strategy

**Question:** During the migration from localStorage-driven to DB-driven verifier queue, how should we handle existing localStorage data?

**Options:**

| Option | Description |
|--------|-------------|
| A: Big bang | On deploy, clear all localStorage verifier keys; start fresh from DB |
| B: Dual-read | Read from DB first; if empty, fall back to localStorage; migrate on first save |
| C: One-time migration endpoint | POST `/verifier/queue/migrate` to bulk-import localStorage items to DB |

**Recommendation:** **Option B** — dual-read with gradual migration. On page load: fetch from DB endpoint first. If the DB queue is empty AND localStorage has items, show a "Migrate existing items?" prompt. On user confirmation, POST each item to the appropriate DB endpoint (create patch/RFI). This preserves existing work without data loss while making the DB authoritative going forward.

---

## 8. Go/No-Go

### Blockers

| Blocker | Severity | Task ID | Resolution Required |
|---------|----------|---------|-------------------|
| RFI batch-scoping decision not made | **HARD BLOCKER** | VER-04 | Must resolve Q1 before VER-11, VER-12, VER-13 can proceed |
| Source-of-truth contract not locked | **SOFT BLOCKER** | VER-01 | Must be locked before any implementation begins (prevents scope creep) |

### Go Recommendation

**Conditional GO** — pending resolution of Q1 (RFI batch-scoping strategy).

Once Q1 is decided and VER-01 is locked, implementation can proceed in this order:

### Recommended Implementation Order

**Phase 1: Foundation (P0)** — Estimated 2-3 days
1. VER-01 — Lock source-of-truth contract
2. VER-04 — Decide RFI batch-scoping (Q1)
3. VER-10 — Add record_id/batch_id filters to patches endpoint
4. VER-11 — Fix batch-level RFI scoping
5. VER-12 — Fix batch health RFI counts
6. VER-13 — Add batch_id filter to workspace-level RFI list

**Phase 2: Composite Endpoint (P1)** — Estimated 2 days
7. VER-14 — Workspace-level corrections list
8. VER-15 — Annotations target filters
9. VER-16 — Composite verifier queue endpoint
10. VER-02, VER-03 — Update API docs

**Phase 3: UI Wiring (P2)** — Estimated 3-4 days
11. VER-17 — Wire vrApprove to DB
12. VER-18 — Wire vrReject to DB
13. VER-19 — Hydrate verifier queue from DB
14. VER-20 — Wire RFI custody transitions
15. VER-21 — Wire correction approvals

**Phase 4: Cleanup (P3-P4)** — Estimated 1-2 days
16. VER-22 — SSE batch filter
17. VER-23 — localStorage migration utility
18. VER-24 — Remove legacy localStorage code

**Phase 5: Audit & Test** — Throughout
19. VER-30–VER-36 — Security audit + integration tests

### Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|-----------|
| localStorage data loss during migration | Medium | Option B (dual-read) preserves existing data |
| Breaking existing analyst workflows | High | All changes are additive; existing localStorage paths continue working until Phase 4 |
| Performance of composite queue endpoint | Low | Three simple queries + in-memory merge; paginated |
| Schema migration complexity | Low | Single additive column (`batch_id` on rfis); no destructive changes |

---

*End of V2.54 Verifier Annotation Layer Doc Phase Audit*
