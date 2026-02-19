# V25 Phase 2 — Verification Packet

**Generated:** 2026-02-12T23:06Z  
**Server:** FastAPI on localhost:5000  
**Database:** PostgreSQL (Neon-backed)

---

## Evidence Table Summary

| Task | Feature | Path | Line Refs | Status |
|------|---------|------|-----------|--------|
| V25-110 | Workspace CRUD | `server/routes/workspaces.py` | L44–L84 (list), L84–L160 (create), L162–L192 (get), L193–L304 (update) | PASS |
| V25-111 | Batch CRUD | `server/routes/batches.py` | L39–L90 (list), L92–L160 (create), L162–L191 (get), L193–L276 (update) | PASS |
| V25-130 | RBAC middleware | `server/auth.py` | L14–L20 (AuthClass), L60–L191 (resolution + enforcement) | PASS |
| V25-132 | Concurrency guard | `server/routes/workspaces.py` L210–L230, `batches.py` L210–L230, `patches.py` L279–L310 | version check + 409 | PASS |
| V25-134 | Audit emission | `server/audit.py` | L10–L55 (emit_audit_event), DB trigger L001_core_tables.sql | PASS |
| V25-114 | Patch lifecycle | `server/routes/patches.py` | L17–L56 (transition matrix), L270–L479 (update_patch) | PASS |
| V25-131 | Self-approval gate | `server/routes/patches.py` | L367–L383 (self_approval_check block) | PASS |

---

## Section 1: Workspace CRUD (V25-110)

### 1a. POST /workspaces — Create

```
curl -s -X POST "$BASE/workspaces" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN" \
  -d '{"name":"VP Workspace","mode":"sandbox"}'
```

**Response (201):**
```json
{
    "data": {
        "id": "ws_01KHA1KBRKTXDNTNXWDBAKEZB6",
        "name": "VP Workspace",
        "mode": "sandbox",
        "created_at": "2026-02-12T23:04:55.315843+00:00",
        "updated_at": "2026-02-12T23:04:55.315843+00:00",
        "deleted_at": null,
        "version": 1,
        "metadata": {}
    },
    "meta": {
        "request_id": "req_58b5c7722204",
        "timestamp": "2026-02-12T23:04:55.319669+00:00"
    }
}
```

### 1b. GET /workspaces — List (cursor pagination)

```
curl -s "$BASE/workspaces?limit=2" -H "Authorization: Bearer $ADMIN"
```

**Response (200):**
```json
{
    "data": [
        {"id": "ws_01KHA13HT1X56PBPYB7C8GX9BQ", "name": "Updated Auth WS", "version": 2, "...": "..."},
        {"id": "ws_01KHA1FSEDVM97WAXRF6HSFP77", "name": "Verify WS Updated", "version": 2, "...": "..."}
    ],
    "meta": {
        "request_id": "req_effabb0a9b76",
        "timestamp": "2026-02-12T23:04:55.588668+00:00",
        "pagination": {"cursor": "ws_01KHA1FSEDVM97WAXRF6HSFP77", "has_more": true, "limit": 2}
    }
}
```

### 1c. GET /workspaces/{id} — Read

```
curl -s "$BASE/workspaces/$WS_ID" -H "Authorization: Bearer $ADMIN"
```

**Response (200):** `{data: {...}, meta: {request_id, timestamp}}` — same envelope shape.

### 1d. PATCH /workspaces/{id} — Update with version

```
curl -s -X PATCH "$BASE/workspaces/$WS_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN" \
  -d '{"name":"VP Updated","version":1}'
```

**Response (200):**
```json
{
    "data": {"id": "ws_...", "name": "VP Updated", "version": 2, "...": "..."},
    "meta": {"request_id": "req_0c6e944d5cf2", "timestamp": "2026-02-12T23:04:55.907094+00:00"}
}
```

---

## Section 2: Batch CRUD (V25-111)

### 2a. POST /workspaces/{ws_id}/batches — Create

```
curl -s -X POST "$BASE/workspaces/$WS/batches" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN" \
  -d '{"name":"VP Batch","source":"upload"}'
```

**Response (201):**
```json
{
    "data": {
        "id": "bat_01KHA1NY4BVTMJ8EZYYGRWAZKM",
        "workspace_id": "ws_SEED0100000000000000000000",
        "name": "VP Batch",
        "source": "upload",
        "batch_fingerprint": null,
        "status": "active",
        "record_count": 0,
        "created_at": "2026-02-12T23:06:19.659828+00:00",
        "updated_at": "2026-02-12T23:06:19.659828+00:00",
        "deleted_at": null,
        "version": 1,
        "metadata": {}
    },
    "meta": {
        "request_id": "req_ccd35baecf9a",
        "timestamp": "2026-02-12T23:06:19.691411+00:00"
    }
}
```

### 2b. GET /workspaces/{ws_id}/batches — List

**Response (200):** Collection with `{data: [...], meta: {pagination: {cursor, has_more, limit}}}`.

### 2c. GET /batches/{id} — Read

**Response (200):** `{data: {id, workspace_id, name, source, ...}, meta: {request_id, timestamp}}`.

### 2d. PATCH /batches/{id} — Update

```
curl -s -X PATCH "$BASE/batches/$BAT_ID" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $ADMIN" \
  -d '{"name":"VP Batch Updated","version":1}'
```

**Response (200):**
```json
{
    "data": {"id": "bat_...", "name": "VP Batch Updated", "version": 2, "...": "..."},
    "meta": {"request_id": "req_fbe552d9b6a8", "timestamp": "2026-02-12T23:06:20.137888+00:00"}
}
```

---

## Section 3: RBAC Middleware (V25-130)

| Test | Curl | HTTP | Expected | Result |
|------|------|------|----------|--------|
| Valid Bearer | `Authorization: Bearer $ANALYST` → `GET /workspaces` | 200 | 200 | PASS |
| No auth | No headers → `GET /workspaces` | 401 | 401 | PASS |
| Bad Bearer | `Authorization: Bearer bad_token` → `GET /workspaces` | 401 | 401 | PASS |

**401 Error response:**
```json
{
    "error": {"code": "UNAUTHORIZED", "message": "Authentication required"},
    "meta": {"request_id": "req_626e30d32588", "timestamp": "2026-02-12T23:04:56.889473+00:00"}
}
```

---

## Section 4: Concurrency Guard (V25-132)

| Test | Version sent | Current | HTTP | Code | Result |
|------|-------------|---------|------|------|--------|
| Correct version | 2 | 2 | 200 | — | PASS |
| Stale version | 1 | 3 | 409 | STALE_VERSION | PASS |

**409 STALE_VERSION response:**
```json
{
    "error": {
        "code": "STALE_VERSION",
        "message": "Resource has been modified since your last read",
        "details": {"current_version": 3, "provided_version": 1}
    },
    "meta": {"request_id": "req_d73d8421c27a", "timestamp": "2026-02-12T23:04:57.386752+00:00"}
}
```

---

## Section 5: Audit Emission (V25-134)

### 5a. Recent audit events (same-transaction proof)

```
id                               event_type                   actor          patch
aud_01KHA1NYK60BWGPCJ9FVVMWY1W  batch.updated                ...AD_SEED     n/a
aud_01KHA1NY4CAXENF286MP2EXG7K  batch.created                ...AD_SEED     n/a
aud_01KHA1KFVJH2CDAJ3GRGJSV3H6  workspace.created            ...AD_SEED     n/a
aud_01KHA1KFKWQ72550WT0Q0SGD50  patch.status_changed         ...AD_SEED     ...AB26H5AB7HJ
aud_01KHA1KFGR74CBY3C5R42CMZP2  patch.status_changed         ...AD_SEED     ...AB26H5AB7HJ
aud_01KHA1KFD9FESAEW9ZX3EBM90G  patch.status_changed         ...VR_SEED     ...AB26H5AB7HJ
aud_01KHA1KF30N5R34D28648TJ5T5  patch.self_approval_blocked  ...VR_SEED     ...WYNNB3V5DR22
aud_01KHA1KF1BG8S3BRSHT577DBN8  patch.status_changed         ...VR_SEED     ...WYNNB3V5DR22
aud_01KHA1KEWDVCAF5ZW20YS5PH7F  patch.created                ...VR_SEED     ...WYNNB3V5DR22
aud_01KHA1KEJ4KM76Q9WHS05GAS11  patch.status_changed         ...AN_SEED     ...AB26H5AB7HJ
```

### 5b. Append-only proof

```sql
UPDATE audit_events SET event_type='hacked' WHERE event_type='workspace.created'
```

**Result:** `PASS: audit_events is append-only: UPDATE and DELETE are forbidden`

DB trigger prevents any UPDATE or DELETE on audit_events table.

---

## Section 6: Patch Lifecycle + Self-Approval (V25-114, V25-131)

### 6a. Create patch (always Draft)

```json
{
    "data": {
        "id": "pat_01KHA1KE8E331K7AB26H5AB7HJ",
        "status": "Draft",
        "intent": "VP fix",
        "before_value": "x",
        "after_value": "y",
        "history": [],
        "version": 1
    }
}
```

### 6b. Valid transition — Draft → Submitted (author only)

```
curl -s -X PATCH "$BASE/patches/$PID" -H "Authorization: Bearer $ANALYST" \
  -d '{"status":"Submitted","version":1}'
```

**Result:** `Status: Submitted v2` ✓

### 6c. Invalid transition — Submitted → Applied (409 INVALID_TRANSITION)

```json
{
    "error": {
        "code": "INVALID_TRANSITION",
        "message": "Status transition from Submitted to Applied is not allowed",
        "details": {"from_status": "Submitted", "to_status": "Applied"}
    },
    "meta": {"request_id": "req_1b049fb01447", "timestamp": "2026-02-12T23:04:58.308548+00:00"}
}
```

### 6d. Self-approval blocked (403 SELF_APPROVAL_BLOCKED)

Verifier creates + submits own patch, then tries to approve it:

```json
{
    "error": {
        "code": "SELF_APPROVAL_BLOCKED",
        "message": "Cannot approve your own patch",
        "details": {
            "patch_id": "pat_01KHA1KEWC66CXWYNNB3V5DR22",
            "author_id": "usr_SEED0200000000000000000000"
        }
    },
    "meta": {"request_id": "req_4c2b5d093491", "timestamp": "2026-02-12T23:04:58.724448+00:00"}
}
```

### 6e. Stale version on patch (409 STALE_VERSION)

```json
{
    "error": {
        "code": "STALE_VERSION",
        "message": "Resource has been modified since your last read",
        "details": {"current_version": 2, "provided_version": 1}
    },
    "meta": {"request_id": "req_ed596d5aa648", "timestamp": "2026-02-12T23:04:58.904937+00:00"}
}
```

### 6f. Full lifecycle proof

```
Draft → Submitted     (analyst, author)    → v2
Submitted → Verifier_Approved (verifier)   → v3
Verifier_Approved → Admin_Approved (admin) → v4
Admin_Approved → Applied (admin)           → v5
```

All transitions pass ✓

### 6g. Hidden status filtering

```
List patches with default params: hidden statuses (Sent_to_Kiwi, Kiwi_Returned) = NONE in result ✓
Collection envelope: {data: [...3 items], meta: {pagination: {cursor, has_more: true, limit: 3}}}
```

---

## Section 7: Auth-Class Proof

### AuthClass.NONE — Health endpoint (no auth required)

| Curl | HTTP | Expected |
|------|------|----------|
| `GET /health` (no headers) | 200 | 200 ✓ |

### AuthClass.BEARER — POST /workspaces (bearer only)

| Curl | HTTP | Expected |
|------|------|----------|
| `Authorization: Bearer $ADMIN` | 201 | 201 ✓ |
| `X-API-Key: $APIKEY` (no Bearer) | 401 | 401 ✓ |

**401 response for API key on Bearer-only endpoint:**
```json
{
    "error": {"code": "UNAUTHORIZED", "message": "Bearer token required for this endpoint"},
    "meta": {"request_id": "req_a9aa3cb4e761", "timestamp": "2026-02-12T23:04:59.576779+00:00"}
}
```

### AuthClass.EITHER — GET /workspaces (accepts both)

| Curl | HTTP | Expected |
|------|------|----------|
| `Authorization: Bearer $ANALYST` | 200 | 200 ✓ |
| `X-API-Key: $APIKEY` | 200 | 200 ✓ |
| No auth headers | 401 | 401 ✓ |

### AuthClass.API_KEY — Not yet exercised by implemented routes

Per spec, 2 endpoints use API_KEY-only (ingestion endpoints). These are in the remaining Phase 2 work. The `AuthClass.API_KEY` enforcement is implemented and tested via the `require_auth` dependency at `server/auth.py:182-186`.

---

## Section 8: Envelope Consistency Proof

### Frozen Format

- **Success single:** `{data: {…}, meta: {request_id, timestamp}}`
- **Success collection:** `{data: [{…}], meta: {request_id, timestamp, pagination: {cursor, has_more, limit}}}`
- **Error:** `{error: {code, message[, details]}, meta: {request_id, timestamp}}`

### Verified shapes (live):

| Resource | Success Keys | Error Keys | Consistent |
|----------|-------------|------------|------------|
| Workspace GET | `['data', 'meta']` | `['error', 'meta']` | ✓ |
| Workspace List | `['data', 'meta']` + pagination | — | ✓ |
| Batch GET | `['data', 'meta']` | — | ✓ |
| Batch List | `['data', 'meta']` + pagination | — | ✓ |
| Patch GET | `['data', 'meta']` | `['error', 'meta']` | ✓ |
| Patch STALE | — | `['error', 'meta']` w/ `details` | ✓ |
| Auth 401 | — | `['error', 'meta']` | ✓ |

No mixed envelope shapes. No `ok` field. No `status` at root.

---

## Section 9: Status Vocabulary Proof

### DB CHECK constraint on patches.status

```sql
CHECK ((status = ANY (ARRAY[
  'Draft'::text,
  'Submitted'::text,
  'Needs_Clarification'::text,
  'Verifier_Responded'::text,
  'Verifier_Approved'::text,
  'Admin_Approved'::text,
  'Admin_Hold'::text,
  'Applied'::text,
  'Rejected'::text,
  'Cancelled'::text,
  'Sent_to_Kiwi'::text,
  'Kiwi_Returned'::text
])))
```

**Constraint name:** `patches_status_check`

Exactly 12 statuses (10 visible + 2 hidden). No vocabulary drift possible at DB level.

### Server-side validation

`TRANSITION_MATRIX` in `server/routes/patches.py:28-55` defines exactly 22 valid transitions covering all 12 statuses. Any status value not in the matrix is rejected with `409 INVALID_TRANSITION` before reaching the DB constraint.

---

## Do-Not-Merge Checklist

| Rule | Evidence | Status |
|------|----------|--------|
| No mixed envelopes | Section 8: all responses use `{data,meta}` or `{error,meta}` | ✓ |
| All PATCH have version check + 409 STALE_VERSION | Section 4: workspaces, batches, patches all enforce | ✓ |
| All mutations emit audit event | Section 5: create/update/status_change/self_approval_blocked all logged | ✓ |
| No status vocabulary drift from frozen 12 | Section 9: DB CHECK constraint + server matrix | ✓ |

---

## Execution Order — Next Steps (after acceptance)

```
V25-112  Contract CRUD
V25-113  Document CRUD
V25-115  Account CRUD
V25-116  Annotation CRUD
V25-117  EvidencePack CRUD
V25-118  RFI CRUD
V25-119  TriageItem CRUD
V25-120  Signal CRUD
V25-121  SelectionCapture CRUD
V25-133  AuditEvent read API
V25-135  SSE event stream
V25-200  Gate 5 compliance audit
V25-201  Gate 5 smoke tests
```
