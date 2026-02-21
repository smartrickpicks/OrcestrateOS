# V2.5 Gate 4 — Lock Checks

**Date:** 2026-02-12
**Status:** Confirmed prior to first line of Gate 4 code

---

## Lock Check 1: Envelope Lock

**Decision: Format B — `{ data, meta }` / `{ error, meta }`**

No `ok` field. This is the format already defined in the canonical spec (Section 4) and OpenAPI schema.

### Success Envelope (single resource)

```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_...",
    "timestamp": "2026-02-12T00:00:00Z"
  }
}
```

### Collection Envelope (list)

```json
{
  "data": [ ... ],
  "meta": {
    "request_id": "req_...",
    "timestamp": "2026-02-12T00:00:00Z",
    "pagination": {
      "cursor": "eyJ...",
      "has_more": true,
      "limit": 50
    }
  }
}
```

### Error Envelope

```json
{
  "error": {
    "code": "STALE_VERSION",
    "message": "Resource has been modified since your last read",
    "details": { "current_version": 5, "provided_version": 3 }
  },
  "meta": {
    "request_id": "req_...",
    "timestamp": "2026-02-12T00:00:00Z"
  }
}
```

### Enforcement Points

| Layer | How Enforced |
|-------|-------------|
| OpenAPI 3.1 | `WorkspaceResponse`, `BatchResponse`, `PatchResponse`, etc. all use `{ data, meta: ResponseMeta }`. `ErrorEnvelope` uses `{ error: { code, message, details }, meta: ResponseMeta }`. No `ok` field anywhere. |
| Server code | Single `envelope()` helper returns `{ "data": ..., "meta": { "request_id": ..., "timestamp": ... } }`. Single `error_envelope()` helper returns `{ "error": { "code": ..., "message": ..., "details": ... }, "meta": ... }`. All routes use these helpers — no ad-hoc dict construction. |
| Smoke tests | Every response assertion checks for `data` key (success) or `error.code` key (failure). Absence of `ok` key is explicitly asserted. |

### Confirmed Consistency

- Canonical spec Section 4: `{ data, meta }` / `{ error, meta }` — **matches**
- OpenAPI `ResponseMeta`, `CollectionMeta`, `ErrorEnvelope` schemas — **matches**
- Contract Lock Section 2.4 — **matches**
- Gate 3 Alignment Packet Section 3.2 — **matches**

---

## Lock Check 2: Patch Status Vocabulary Lock

**Frozen: 12 statuses (10 visible + 2 hidden)**

### Canonical Status List

| # | Status | Visibility | Category |
|---|--------|-----------|----------|
| 1 | `Draft` | Visible | Initial |
| 2 | `Submitted` | Visible | In-review |
| 3 | `Needs_Clarification` | Visible | In-review |
| 4 | `Verifier_Responded` | Visible | In-review |
| 5 | `Verifier_Approved` | Visible | Approved |
| 6 | `Admin_Approved` | Visible | Approved |
| 7 | `Admin_Hold` | Visible | Hold |
| 8 | `Applied` | Visible | Terminal |
| 9 | `Rejected` | Visible | Terminal |
| 10 | `Cancelled` | Visible | Terminal |
| 11 | `Sent_to_Kiwi` | Hidden | Integration |
| 12 | `Kiwi_Returned` | Hidden | Integration |

### Enforcement Points

| Layer | How Enforced |
|-------|-------------|
| OpenAPI `PatchUpdate.status` enum | All 12 values listed (lines 717-728 of openapi.yaml) — **confirmed** |
| DB `CHECK` constraint | `001_core_tables.sql` will define `CHECK (status IN ('Draft','Submitted','Needs_Clarification','Verifier_Responded','Verifier_Approved','Admin_Approved','Admin_Hold','Applied','Rejected','Cancelled','Sent_to_Kiwi','Kiwi_Returned'))` on the `patches` table |
| Server transition matrix | Python dict maps every valid `(from_status, to_status)` → `required_role`. Invalid pairs rejected with 409 `INVALID_TRANSITION`. Only these 12 values are keys. |
| RBAC gates | Role check on each transition per canonical spec Section 7 transition matrix |
| Default query filter | `GET /patches` excludes `Sent_to_Kiwi` and `Kiwi_Returned` unless `?include_hidden=true` |
| Smoke tests | Full lifecycle test: `Draft → Submitted → Verifier_Approved → Admin_Approved → Applied`. Blocked transition test (e.g., `Draft → Applied` returns 409). Hidden status exclusion test. |

### Confirmed Consistency

- Canonical spec Section 7: 12 statuses — **matches**
- OpenAPI `PatchUpdate` enum: 12 values — **matches**
- Locked Decisions D5: "12-status lifecycle (10 visible + 2 hidden)" — **matches**
- Contract Lock Section 5: all 12 listed — **matches**
- Gate 3 Alignment Packet Section 3.3: all 12 listed — **matches**

---

## Lock Check 3: Auth Scope Lock

**Frozen endpoint-auth mapping table:**

### Auth Class Definitions

| Auth Class | Token Required | Header |
|-----------|---------------|--------|
| **Bearer only** | Google OAuth JWT | `Authorization: Bearer {jwt}` |
| **API key only** | Workspace-scoped key | `X-API-Key: {key}` |
| **Either** | JWT or API key | Either header accepted |
| **None** | No auth | — |

### Complete Endpoint-Auth Mapping

| Endpoint | Method | Auth Class | Rationale |
|----------|--------|-----------|-----------|
| `/api/v2.5/health` | GET | **None** | System health, no data exposure |
| `/api/v2.5/workspaces` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/workspaces` | POST | **Bearer only** | Human-governed workspace creation |
| `/api/v2.5/workspaces/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/workspaces/{id}` | PATCH | **Bearer only** | Human-governed mutation |
| `/api/v2.5/workspaces/{ws_id}/batches` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/workspaces/{ws_id}/batches` | POST | **Either** | Service ingestion OR human upload |
| `/api/v2.5/batches/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/batches/{id}` | PATCH | **Bearer only** | Human-governed mutation |
| `/api/v2.5/batches/{bat_id}/contracts` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/batches/{bat_id}/contracts` | POST | **Bearer only** | Human-governed creation |
| `/api/v2.5/contracts/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/contracts/{id}` | PATCH | **Bearer only** | Human-governed mutation |
| `/api/v2.5/contracts/{ctr_id}/documents` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/contracts/{ctr_id}/documents` | POST | **Bearer only** | Human-governed creation |
| `/api/v2.5/documents/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/documents/{id}` | PATCH | **Bearer only** | Human-governed mutation |
| `/api/v2.5/batches/{bat_id}/accounts` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/batches/{bat_id}/accounts` | POST | **Bearer only** | Human-governed creation |
| `/api/v2.5/accounts/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/accounts/{id}` | PATCH | **Bearer only** | Human-governed mutation |
| `/api/v2.5/workspaces/{ws_id}/patches` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/workspaces/{ws_id}/patches` | POST | **Bearer only** | Human-governed creation |
| `/api/v2.5/patches/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/patches/{id}` | PATCH | **Bearer only** | Human-governed transition |
| `/api/v2.5/patches/{pat_id}/evidence-packs` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/patches/{pat_id}/evidence-packs` | POST | **Bearer only** | Human-governed creation |
| `/api/v2.5/evidence-packs/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/evidence-packs/{id}` | PATCH | **Bearer only** | Human-governed mutation |
| `/api/v2.5/workspaces/{ws_id}/annotations` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/workspaces/{ws_id}/annotations` | POST | **Bearer only** | Human-governed creation |
| `/api/v2.5/annotations/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/annotations/{id}` | PATCH | **Bearer only** | Human-governed mutation |
| `/api/v2.5/workspaces/{ws_id}/rfis` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/workspaces/{ws_id}/rfis` | POST | **Bearer only** | Human-governed creation |
| `/api/v2.5/rfis/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/rfis/{id}` | PATCH | **Bearer only** | Human-governed mutation |
| `/api/v2.5/batches/{bat_id}/triage-items` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/batches/{bat_id}/triage-items` | POST | **API key only** | Service ingestion |
| `/api/v2.5/triage-items/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/triage-items/{id}` | PATCH | **Bearer only** | Human-governed resolution |
| `/api/v2.5/batches/{bat_id}/signals` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/batches/{bat_id}/signals` | POST | **API key only** | Service ingestion |
| `/api/v2.5/signals/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/documents/{doc_id}/selection-captures` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/documents/{doc_id}/selection-captures` | POST | **Bearer only** | Human-governed creation |
| `/api/v2.5/selection-captures/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/workspaces/{ws_id}/audit-events` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/audit-events/{id}` | GET | **Either** | Read — dual-accept |
| `/api/v2.5/workspaces/{ws_id}/events/stream` | GET | **Either** | SSE — dual-accept |

### Auth Class Summary

| Auth Class | Count | Endpoints |
|-----------|-------|-----------|
| **None** | 1 | Health |
| **Bearer only** | 19 | All human-governed POST (except batch), all PATCH, workspace POST |
| **API key only** | 2 | POST /triage-items, POST /signals |
| **Either** | 28 | All GET (reads), POST /batches, SSE stream |

### Smoke Test Auth Assertions

| Test | Expected Result |
|------|----------------|
| `GET /health` with no auth | 200 |
| `GET /workspaces` with Bearer | 200 |
| `GET /workspaces` with API key | 200 |
| `GET /workspaces` with no auth | 401 `UNAUTHORIZED` |
| `POST /workspaces` with Bearer | 201 |
| `POST /workspaces` with API key only | 401 `UNAUTHORIZED` |
| `POST /signals` with API key | 201 |
| `POST /signals` with Bearer only | 401 `UNAUTHORIZED` |
| `PATCH /patches/{id}` with Bearer | 200 |
| `PATCH /patches/{id}` with API key only | 401 `UNAUTHORIZED` |
| `GET /patches` with expired Bearer | 401 `UNAUTHORIZED` |
| `GET /patches` with revoked API key | 401 `UNAUTHORIZED` |

### Confirmed Consistency

- Canonical spec Section 5 endpoint auth policy: 4 categories — **matches**
- OpenAPI `securitySchemes`: `BearerToken`, `ScopedApiKey`, `GoogleOAuth` — **matches**
- Locked Decisions D2: "dual-mode auth" — **matches**
- Contract Lock Section 4: auth policy table — **matches**

---

## Confirmation Statement

All three lock checks are confirmed consistent across:
- `docs/api/API_SPEC_V2_5_CANONICAL.md` (canonical spec)
- `docs/api/openapi.yaml` (machine-readable spec)
- `docs/handoff/V25_LOCKED_DECISIONS.md` (frozen decisions)
- `docs/handoff/V25_CONTRACT_LOCK.md` (contract freeze)
- `docs/handoff/V25_GATE3_ALIGNMENT_PACKET.md` (alignment packet)

**Gate 4 implementation may now proceed per the approved V25 task plan and sequencing.**
