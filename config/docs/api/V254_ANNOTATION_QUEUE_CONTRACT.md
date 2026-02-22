# V2.54 Annotation Queue Contract — Operations View

**Version:** 2.54  
**Date:** 2026-02-17  
**Status:** LOCKED — Clarity Phase  
**Scope:** Normalized queue item shape, multi-batch Operations View, endpoint contract plan  

---

## 1. Naming Standard

**Use "Operations View" consistently** in all code, UI labels, API documentation, and decision docs.

Do NOT use:
- ~~"All"~~ (ambiguous)
- ~~"Verifier Dashboard"~~ (legacy name)
- ~~"Triage"~~ (already used for analyst triage page)
- ~~"Queue"~~ alone (too generic)

The Operations View is the multi-batch, DB-first workspace-level queue where verifiers and admins review governance items.

---

## 2. Operations View Queue Contract

### 2.1 Normalized Queue Item Shape

All annotation artifacts (patches, RFIs, corrections) are normalized to a single unified shape for the Operations View:

```typescript
interface OperationsQueueItem {
  id: string;
  item_type: 'patch' | 'rfi' | 'correction';

  workspace_id: string;
  batch_id: string | null;
  contract_id: string | null;
  document_id: string | null;
  record_id: string | null;
  field_key: string | null;

  lifecycle_status: string;
  queue_status: 'pending' | 'needs_clarification' | 'sent_to_admin' | 'resolved';
  custody_owner_id: string | null;
  custody_owner_role: 'analyst' | 'verifier' | 'admin' | null;

  author_id: string;
  author_email: string | null;
  decided_by: string | null;

  summary: string;
  before_value: string | null;
  after_value: string | null;

  created_at: string;
  updated_at: string;
  resolved_at: string | null;

  version: number;
  metadata: object;
}
```

### 2.2 Queue Status Mapping

Each artifact type maps its native lifecycle status to a normalized `queue_status`:

| Artifact | Native Status Field | Native Value | → queue_status |
|----------|-------------------|--------------|----------------|
| **Patch** | `patches.status` | `Submitted` | `pending` |
| Patch | | `Needs_Clarification` | `needs_clarification` |
| Patch | | `Verifier_Responded` | `pending` |
| Patch | | `Verifier_Approved` | `sent_to_admin` |
| Patch | | `Admin_Hold` | `sent_to_admin` |
| Patch | | `Admin_Approved` | `resolved` |
| Patch | | `Applied` | `resolved` |
| Patch | | `Rejected` | `resolved` |
| Patch | | `Cancelled` | `resolved` |
| Patch | | `Sent_to_Kiwi` | `sent_to_admin` |
| Patch | | `Kiwi_Returned` | `sent_to_admin` |
| Patch | | `Draft` | *(excluded from queue)* |
| **RFI** | `rfis.custody_status` | `open` | `pending` |
| RFI | | `awaiting_verifier` | `pending` |
| RFI | | `returned_to_analyst` | `needs_clarification` |
| RFI | | `resolved` | `resolved` |
| RFI | | `dismissed` | `resolved` |
| **Correction** | `corrections.status` | `pending_verifier` | `pending` |
| Correction | | `approved` | `resolved` |
| Correction | | `rejected` | `resolved` |

### 2.3 Queue Grouping Across Multiple Batches

The Operations View is workspace-scoped and shows items across ALL batches in the workspace. Grouping and filtering options:

| Dimension | Filter Param | Description |
|-----------|-------------|-------------|
| Queue tab | `queue_status` | Primary filter: pending, needs_clarification, sent_to_admin, resolved |
| Batch | `batch_id` | Narrow to a specific batch (optional) |
| Item type | `item_type` | Filter by patch/rfi/correction (optional) |
| Author | `author_id` | Filter by who created the item (optional) |
| Field | `field_key` | Filter by target field (optional) |

### 2.4 Queue Counts Response Shape

```typescript
interface OperationsQueueCounts {
  pending: number;
  needs_clarification: number;
  sent_to_admin: number;
  resolved: number;
  total: number;
}
```

Counts reflect the current workspace-level totals (or batch-filtered if `batch_id` is provided). They power the tab badges in the UI.

---

## 3. Endpoint Contract Plan

### 3.1 Conventions

All endpoints follow existing `/api/v2.5` conventions:
- **Envelope:** `{ "data": ..., "meta": { "cursor": ..., "has_more": ..., "limit": ... } }`
- **Error envelope:** `{ "error": { "code": "...", "message": "...", "details": ... } }`
- **Pagination:** Cursor-based with `cursor` and `limit` query params
- **Auth:** `Authorization: Bearer <jwt>` or `X-Api-Key: <key>`
- **Workspace isolation:** Every endpoint validates user has a role in the target workspace
- **Optimistic concurrency:** PATCH endpoints require `version` field; return 409 `STALE_VERSION` on conflict
- **Audit events:** All mutating operations emit an `audit_event` row

### 3.2 Existing Endpoints to Reuse (No Changes)

| # | Method | Path | Purpose | Operations View Use |
|---|--------|------|---------|---------------------|
| E1 | GET | `/patches/{pat_id}` | Get single patch | Verifier review detail |
| E2 | PATCH | `/patches/{pat_id}` | Status transition | vrApprove, vrReject |
| E3 | GET | `/rfis/{rfi_id}` | Get single RFI | RFI detail in review |
| E4 | PATCH | `/rfis/{rfi_id}` | Custody transition | Verifier responds/resolves/dismisses |
| E5 | POST | `/documents/{doc}/corrections` | Create correction | Verifier-initiated correction |
| E6 | PATCH | `/corrections/{cor_id}` | Approve/reject correction | Correction decision |
| E7 | GET | `/documents/{doc}/anchors` | List anchors | Evidence anchors for review |
| E8 | GET | `/workspaces/{ws}/events/stream` | SSE real-time events | Live queue updates |
| E9 | POST | `/workspaces/{ws}/annotations` | Create annotation | Verifier notes/flags |
| E10 | PATCH | `/annotations/{ann_id}` | Update annotation | Edit verifier notes |

### 3.3 Existing Endpoints to Extend (Additive Query Params Only)

#### EP-01: Add `record_id` and `batch_id` to `GET /workspaces/{ws}/patches`

**Current params:** `status`, `author_id`, `cursor`, `limit`  
**New params:** `record_id` (TEXT, optional), `batch_id` (TEXT, optional)

```
GET /api/v2.5/workspaces/{ws_id}/patches?batch_id=bat_01JK...&status=Submitted
```

**Implementation:** Add WHERE clauses to `list_patches` (patches.py L89–149):
```sql
-- When record_id provided:
AND record_id = %(record_id)s
-- When batch_id provided:
AND batch_id = %(batch_id)s
```

**Response:** Existing `collection_envelope` — no change.  
**RBAC:** Existing `require_auth(AuthClass.EITHER)` — no change.  
**Audit:** None (read-only).

#### EP-02: Add `batch_id` to `GET /workspaces/{ws}/rfis`

**Current params:** `status`, `custody_status`, `cursor`, `limit`  
**New params:** `batch_id` (TEXT, optional)

```
GET /api/v2.5/workspaces/{ws_id}/rfis?batch_id=bat_01JK...&custody_status=awaiting_verifier
```

**Implementation:** Depends on VER-04 decision (see Annotation Layer Artifact Spec §2.5):
- If `batch_id` column added to `rfis`: simple WHERE clause
- If no column: subquery `AND rfis.patch_id IN (SELECT id FROM patches WHERE batch_id = %(batch_id)s)`

**Response:** Existing `collection_envelope` — no change.  
**RBAC:** Existing — no change.  
**Audit:** None (read-only).

#### EP-03: Add `target_type` and `target_id` to `GET /workspaces/{ws}/annotations`

**Current params:** `cursor`, `limit`  
**New params:** `target_type` (TEXT, optional), `target_id` (TEXT, optional)

```
GET /api/v2.5/workspaces/{ws_id}/annotations?target_type=patch&target_id=pat_01JK...
```

**Implementation:** Add WHERE clauses to `list_annotations` (annotations.py L36+):
```sql
-- When target_type provided:
AND target_type = %(target_type)s
-- When target_id provided:
AND target_id = %(target_id)s
```

**Response:** Existing `collection_envelope` — no change.  
**RBAC:** Existing — no change.  
**Audit:** None (read-only).

### 3.4 Existing Endpoints to Fix (Bug Fixes)

#### EP-04: Fix `GET /batches/{bat_id}/rfis` batch-scoping

**Current behavior (BUG):** `list_batch_rfis` (rfis.py L500–501) extracts `workspace_id` from the batch, then queries `rfis WHERE workspace_id = %s`. This returns ALL workspace RFIs, not batch-scoped ones.

**Fixed behavior:** Return only RFIs belonging to records/patches in the target batch.

**Implementation (depends on VER-04):**
- If `batch_id` column added to `rfis`: `WHERE batch_id = %(bat_id)s`
- If no column: `WHERE patch_id IN (SELECT id FROM patches WHERE batch_id = %(bat_id)s)`

**Response:** Existing `collection_envelope` — no change.  
**RBAC:** Existing — no change.  
**Audit:** None (read-only).

#### EP-05: Fix `GET /batches/{bat_id}/health` RFI counts

**Current behavior (BUG):** batch_health.py L40–51 counts RFIs by `workspace_id` from the batch, returning workspace-wide counts instead of batch-scoped.

**Fixed behavior:** Count only RFIs belonging to the target batch.

**Implementation:** Same approach as EP-04.  
**Response:** Existing shape — no change.

### 3.5 New Endpoints

#### EP-06: `GET /workspaces/{ws}/corrections` — Workspace-Level Correction List

**Method:** GET  
**Path:** `/api/v2.5/workspaces/{ws_id}/corrections`  
**Query Params:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `status` | TEXT | No | Filter by correction status: `pending_verifier`, `approved`, `rejected` |
| `batch_id` | TEXT | No | Filter by batch (via document→batch join) |
| `cursor` | TEXT | No | Pagination cursor |
| `limit` | INT | No | Page size (default 50, max 200) |

**Response:**
```json
{
  "data": [
    {
      "id": "cor_01JK...",
      "document_id": "doc_01JK...",
      "workspace_id": "ws_SEED...",
      "anchor_id": "anc_01JK...",
      "rfi_id": null,
      "field_id": "contract_name",
      "field_key": "contract_name",
      "original_value": "Acme Corp",
      "corrected_value": "ACME Corporation",
      "correction_type": "non_trivial",
      "status": "pending_verifier",
      "decided_by": null,
      "decided_at": null,
      "created_by": "usr_01JK...",
      "created_at": "2026-02-17T10:00:00Z",
      "updated_at": "2026-02-17T10:00:00Z",
      "version": 1,
      "metadata": {}
    }
  ],
  "meta": { "cursor": null, "has_more": false, "limit": 50 }
}
```

**RBAC:** `require_auth(AuthClass.EITHER)` + workspace membership check.  
**Audit:** None (read-only).

#### EP-07: `GET /workspaces/{ws}/operations/queue` — Composite Operations View Queue

**Method:** GET  
**Path:** `/api/v2.5/workspaces/{ws_id}/operations/queue`  
**Query Params:**

| Param | Type | Required | Description |
|-------|------|----------|-------------|
| `queue_status` | TEXT | No | Filter: `pending`, `needs_clarification`, `sent_to_admin`, `resolved` |
| `batch_id` | TEXT | No | Narrow to a specific batch |
| `item_type` | TEXT | No | Filter: `patch`, `rfi`, `correction` |
| `author_id` | TEXT | No | Filter by author |
| `cursor` | TEXT | No | Pagination cursor |
| `limit` | INT | No | Page size (default 50, max 200) |

**Response:**
```json
{
  "data": {
    "items": [
      {
        "id": "pat_01JK...",
        "item_type": "patch",
        "workspace_id": "ws_SEED...",
        "batch_id": "bat_01JK...",
        "contract_id": null,
        "document_id": null,
        "record_id": "rec_142",
        "field_key": "label_vendor",
        "lifecycle_status": "Submitted",
        "queue_status": "pending",
        "custody_owner_id": null,
        "custody_owner_role": null,
        "author_id": "usr_01JK...",
        "author_email": "analyst@example.com",
        "decided_by": null,
        "summary": "Set label_vendor = 'Sony Music' for LICENSING contract",
        "before_value": null,
        "after_value": "Sony Music",
        "created_at": "2026-02-17T09:30:00Z",
        "updated_at": "2026-02-17T09:30:00Z",
        "resolved_at": null,
        "version": 1,
        "metadata": {}
      }
    ],
    "counts": {
      "pending": 12,
      "needs_clarification": 3,
      "sent_to_admin": 5,
      "resolved": 8,
      "total": 28
    }
  },
  "meta": { "cursor": null, "has_more": false, "limit": 50 }
}
```

**Implementation:** New route file `server/routes/operations_queue.py`.

Query strategy:
1. Query `patches` WHERE workspace_id = ws_id AND status != 'Draft' AND deleted_at IS NULL
2. Query `rfis` WHERE workspace_id = ws_id AND deleted_at IS NULL
3. Query `corrections` WHERE workspace_id = ws_id AND deleted_at IS NULL (via JOIN on documents)
4. Map each to `OperationsQueueItem` shape using queue_status mapping (§2.2)
5. Apply `queue_status`, `batch_id`, `item_type`, `author_id` filters
6. Sort by `created_at DESC`
7. Apply cursor pagination
8. Compute `counts` (unfiltered by item_type/author, but filtered by batch_id if provided)

**RBAC:** `require_auth(AuthClass.BEARER)` + role >= `verifier` for full queue, `analyst` for own items only.  
**Audit:** None (read-only).

### 3.6 Endpoint Summary Table

| ID | Method | Path | Type | Status |
|----|--------|------|------|--------|
| E1–E10 | (various) | (various) | Reuse | No changes |
| EP-01 | GET | `/workspaces/{ws}/patches` | Extend | Add record_id, batch_id params |
| EP-02 | GET | `/workspaces/{ws}/rfis` | Extend | Add batch_id param |
| EP-03 | GET | `/workspaces/{ws}/annotations` | Extend | Add target_type, target_id params |
| EP-04 | GET | `/batches/{bat}/rfis` | Fix | Batch-scope the query |
| EP-05 | GET | `/batches/{bat}/health` | Fix | Batch-scope the RFI counts |
| EP-06 | GET | `/workspaces/{ws}/corrections` | New | Workspace-level correction list |
| EP-07 | GET | `/workspaces/{ws}/operations/queue` | New | Composite Operations View queue |

---

## 4. Wire Protocol: UI → API

### 4.1 vrApprove() Wire Protocol

```
UI: vrApprove() clicked
  → Validate: checklist confirmed, not self-approval (client-side pre-check)
  → PATCH /api/v2.5/patches/{pat_id}
    Body: { "status": "Verifier_Approved", "version": currentVersion }
    Headers: Authorization: Bearer <jwt>
  → On 200: Update local queue item, show success toast, refresh queue
  → On 409 STALE_VERSION: Show "This item was modified by someone else. Refreshing..."
     → GET /api/v2.5/patches/{pat_id}
     → Update local state with fresh data
  → On 403 SELF_APPROVAL_BLOCKED: Show error toast "Cannot approve your own patch"
  → On 403 ROLE_NOT_ALLOWED: Show error toast "Insufficient permissions"
```

### 4.2 vrReject() Wire Protocol

```
UI: vrReject() clicked
  → Validate: rejection notes provided (client-side pre-check)
  → PATCH /api/v2.5/patches/{pat_id}
    Body: { "status": "Rejected", "version": currentVersion, "metadata": { "rejection_reason": notes } }
    Headers: Authorization: Bearer <jwt>
  → On 200: Update local queue item, show info toast, refresh queue
  → On 409/403: Same handling as vrApprove
```

### 4.3 RFI Custody Transition Wire Protocol

```
UI: Verifier resolves RFI
  → PATCH /api/v2.5/rfis/{rfi_id}
    Body: { "custody_status": "resolved", "version": currentVersion }
    Headers: Authorization: Bearer <jwt>
  → On 200: Update local queue item, show success toast
  → On 409/403: Same handling as above
```

### 4.4 Correction Approval Wire Protocol

```
UI: Verifier approves correction
  → PATCH /api/v2.5/corrections/{cor_id}
    Body: { "status": "approved", "version": currentVersion }
    Headers: Authorization: Bearer <jwt>
  → On 200: Update local queue item, show success toast
  → On 409/403: Same handling as above
```

### 4.5 Queue Hydration Wire Protocol

```
UI: Page load / mode switch to Operations View
  → GET /api/v2.5/workspaces/{ws_id}/operations/queue?queue_status=pending
    Headers: Authorization: Bearer <jwt>
  → On 200: Populate verifierQueueState from response.data.items
             Update tab counts from response.data.counts
             Clear any stale localStorage queue data
  → On 401/403: Show login prompt or "no access" message
  → On network error: Fall back to localStorage cache with "offline" indicator
```

---

*End of V2.54 Annotation Queue Contract*
