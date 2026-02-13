# API v2.5 Canonical Specification

**Version:** 2.5.0-draft
**Date:** 2026-02-12
**Status:** Gate 3 Complete — Ready for Implementation

---

## 1. Overview

API v2.5 provides resource-style HTTP endpoints for Orchestrate OS governance operations. All durable state is Postgres-backed. Audit events are server-emitted on every write. BroadcastChannel is local UX sync only.

**Base URL:** `/api/v2.5/`

**Resource count:** 14 primary resources (Workspace, Batch, Account, Contract, Document, Patch, Evidence Pack, Annotation, RFI, Triage Item, Signal, Selection Capture, Audit Event, User) plus 1 join table (Annotation Link). User resource is authentication-managed, not CRUD-exposed.

---

## 2. Design Principles

1. Resource-based routes with plural nouns — no verb endpoints
2. PATCH for status transitions and partial updates
3. POST for resource creation with idempotency support
4. GET for reads with cursor-based pagination
5. Prefixed ULID-like primary IDs (sortable, globally unique)
6. Deterministic fingerprints as secondary indexed fields
7. Optimistic concurrency via `version` field on PATCH (409 STALE_VERSION on conflict)
8. Append-only audit events on all mutating endpoints
9. Server-Sent Events (SSE) for cross-user real-time delivery
10. No self-approval on final patch promotion

---

## 3. ID Format

All primary IDs follow the pattern: `{prefix}_{ulid}`

| Prefix | Resource | Example |
|--------|----------|---------|
| `ws_` | Workspace | `ws_01HXYZ...` |
| `bat_` | Batch | `bat_01HXYZ...` |
| `acc_` | Account | `acc_01HXYZ...` |
| `ctr_` | Contract | `ctr_01HXYZ...` |
| `doc_` | Document | `doc_01HXYZ...` |
| `pat_` | Patch | `pat_01HXYZ...` |
| `evp_` | Evidence Pack | `evp_01HXYZ...` |
| `sig_` | Signal | `sig_01HXYZ...` |
| `tri_` | Triage Item | `tri_01HXYZ...` |
| `aud_` | Audit Event | `aud_01HXYZ...` |
| `rfi_` | RFI | `rfi_01HXYZ...` |
| `ann_` | Annotation | `ann_01HXYZ...` |
| `sel_` | Selection Capture | `sel_01HXYZ...` |
| `usr_` | User | `usr_01HXYZ...` |

**ULID component:** 10-char Crockford Base32 timestamp + 16-char random.

**Fingerprint fields:** Hash-based secondary identifiers (e.g., `contract_fingerprint`) are stored alongside ULID primary keys for deduplication and backward compatibility with V2.3 ID model.

---

## 4. Response Envelope

### Success Envelope

```json
{
  "data": { ... },
  "meta": {
    "request_id": "req_...",
    "timestamp": "2026-02-12T00:00:00Z"
  }
}
```

### Collection Envelope

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

### Standard Error Codes

| HTTP Status | Code | Description |
|-------------|------|-------------|
| 400 | `INVALID_REQUEST` | Malformed request body or parameters |
| 401 | `UNAUTHORIZED` | Missing or invalid authentication |
| 403 | `FORBIDDEN` | Insufficient role permissions |
| 403 | `SELF_APPROVAL_BLOCKED` | Cannot approve own patch |
| 404 | `NOT_FOUND` | Resource does not exist |
| 409 | `STALE_VERSION` | Optimistic concurrency conflict |
| 409 | `DUPLICATE_RESOURCE` | Idempotency key collision with different payload |
| 409 | `INVALID_TRANSITION` | Status transition not allowed |
| 422 | `VALIDATION_ERROR` | Request body fails schema validation |
| 429 | `RATE_LIMITED` | Too many requests (future) |
| 500 | `INTERNAL_ERROR` | Unexpected server error |

---

## 5. Authentication and RBAC

### Authentication (Gate 2 Locked)

Dual-mode authentication:

- **Production (human users):** Google OAuth 2.0 (OIDC) with email-based identity resolution
- **Sandbox/service ingestion:** Scoped API keys via `X-API-Key` header

### Endpoint Auth Policy

| Category | Auth Required | Token Type | Examples |
|----------|--------------|-----------|----------|
| **Human-governed** | Google OAuth user token | Bearer JWT | PATCH /patches/{id}, POST /patches, POST /annotations |
| **Service ingestion** | Scoped API key | `X-API-Key` header | POST /signals, POST /triage-items, POST /batches |
| **Read endpoints** | Either token type | Bearer or API key | GET /patches, GET /audit-events, GET /workspaces |
| **Health/system** | None | N/A | GET /health |

### API Key Model

- Keys are workspace-scoped: each key is bound to exactly one `workspace_id`
- Keys carry explicit scopes (e.g., `signals:write`, `batches:write`, `read:all`)
- Key metadata: `key_id`, `workspace_id`, `scopes[]`, `created_by` (usr_), `created_at`, `expires_at`, `last_used_at`
- Keys are stored hashed; only the prefix is visible after creation
- Revocation is immediate and audited

### OAuth Flow

1. Client redirects to Google OAuth consent screen
2. Google returns authorization code
3. Server exchanges code for ID token (OIDC)
4. Server validates ID token, extracts email
5. Server resolves email to `usr_` ID and workspace roles
6. Server issues session token (JWT, 1h expiry, refresh via /auth/refresh)
7. All subsequent requests include `Authorization: Bearer {token}`

### Role Model

| Role | Permissions |
|------|------------|
| **Analyst** | Create/edit drafts, submit patches, respond to clarification, view own patches, assemble evidence |
| **Verifier** | All Analyst permissions + review any patch, request clarification, approve/reject at verifier gate |
| **Admin** | All Verifier permissions + admin approve, admin hold, promote to baseline, export, access admin console |
| **Architect** | All Admin permissions + TruthPack calibration, schema editing, system configuration |

### RBAC Enforcement

- Every mutating endpoint checks `actor_role` against the required permission
- Role is resolved from the authenticated user's `user_workspace_roles` entry for the target workspace
- No implicit role escalation
- Workspace-scoped: a user may have different roles in different workspaces

### Workspace Isolation (Gate 2 Locked)

- Single Postgres database for all workspaces
- `workspace_id` is a mandatory foreign key on all governed resource tables
- Every query includes `workspace_id` in its WHERE clause — enforced at repository layer
- Cross-workspace queries are architecturally forbidden
- Composite indexes use `workspace_id` as leading column
- Optional RLS hardening via session variable (`app.workspace_id`)

### No-Self-Approval Rule

- PATCH to `Verifier_Approved`: server rejects if `actor_id === patch.author_id` (403 `SELF_APPROVAL_BLOCKED`)
- PATCH to `Admin_Approved`: server rejects if `actor_id === patch.author_id` (403 `SELF_APPROVAL_BLOCKED`)
- This is enforced server-side regardless of client behavior
- Cannot be overridden by any role including Architect

---

## 6. Resource Schemas

### 6.1 Workspace

```
{
  "id": "ws_...",              // ULID primary key
  "name": "string",
  "mode": "sandbox|production",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "version": integer,
  "metadata": {}               // JSONB
}
```

### 6.2 Batch

```
{
  "id": "bat_...",
  "workspace_id": "ws_...",
  "name": "string",
  "source": "upload|merge|import",
  "batch_fingerprint": "string",     // V2.3 hash-based ID
  "status": "active|archived",
  "record_count": integer,
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "version": integer,
  "metadata": {}
}
```

### 6.3 Account

```
{
  "id": "acc_...",
  "batch_id": "bat_...",
  "workspace_id": "ws_...",
  "account_name": "string",
  "billing_country": "string|null",
  "billing_city": "string|null",
  "account_fingerprint": "string",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "version": integer,
  "metadata": {}
}
```

### 6.4 Contract

```
{
  "id": "ctr_...",
  "batch_id": "bat_...",
  "account_id": "acc_...|null",
  "workspace_id": "ws_...",
  "contract_fingerprint": "string",   // V2.3 ctr_{hash} value
  "contract_id_source": "extracted|url_hash|fallback_sig",
  "file_url": "string|null",
  "file_name": "string|null",
  "status": "active|archived",
  "health_score": integer|null,       // 0-100
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "version": integer,
  "metadata": {}
}
```

### 6.5 Document

```
{
  "id": "doc_...",
  "contract_id": "ctr_...",
  "batch_id": "bat_...",
  "workspace_id": "ws_...",
  "document_fingerprint": "string",   // V2.3 doc_{hash} value
  "file_url": "string|null",
  "file_name": "string|null",
  "section_name": "string|null",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "version": integer,
  "metadata": {}
}
```

### 6.6 Patch

```
{
  "id": "pat_...",
  "workspace_id": "ws_...",
  "batch_id": "bat_...",
  "record_id": "string",
  "field_key": "string",
  "author_id": "usr_...",
  "status": "Draft|Submitted|Needs_Clarification|Verifier_Responded|Verifier_Approved|Admin_Approved|Admin_Hold|Applied|Rejected|Cancelled|Sent_to_Kiwi|Kiwi_Returned",
  "intent": "string",
  "when_clause": {},
  "then_clause": [],
  "because_clause": "string|null",
  "evidence_pack_id": "evp_...|null",
  "submitted_at": "ISO-8601|null",
  "resolved_at": "ISO-8601|null",
  "file_name": "string|null",
  "file_url": "string|null",
  "before_value": "string|null",
  "after_value": "string|null",
  "history": [],
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "version": integer,
  "metadata": {}
}
```

### 6.7 Evidence Pack

```
{
  "id": "evp_...",
  "patch_id": "pat_...",          // Patch-scoped ownership
  "workspace_id": "ws_...",
  "author_id": "usr_...",
  "blocks": {
    "context": {},
    "data_reference": {},
    "pdf_anchor": {},
    "rationale": {}
  },
  "status": "incomplete|complete",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "version": integer,
  "metadata": {}
}
```

### 6.8 Annotation

```
{
  "id": "ann_...",
  "workspace_id": "ws_...",
  "author_id": "usr_...",
  "target_type": "field|record|contract|document",
  "target_id": "string",
  "content": "string",
  "annotation_type": "note|flag|question",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "version": integer,
  "metadata": {}
}
```

### 6.9 Annotation Link

```
{
  "id": "string",                // Composite or generated
  "annotation_id": "ann_...",
  "linked_type": "patch|rfi|evidence_pack|selection_capture",
  "linked_id": "string",
  "created_at": "ISO-8601"
}
```

### 6.10 RFI (Request for Information)

```
{
  "id": "rfi_...",
  "workspace_id": "ws_...",
  "patch_id": "pat_...|null",
  "author_id": "usr_...",
  "target_record_id": "string",
  "target_field_key": "string|null",
  "question": "string",
  "response": "string|null",
  "responder_id": "usr_...|null",
  "status": "open|responded|closed",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "version": integer,
  "metadata": {}
}
```

### 6.11 Triage Item

```
{
  "id": "tri_...",
  "workspace_id": "ws_...",
  "batch_id": "bat_...",
  "record_id": "string",
  "field_key": "string|null",
  "issue_type": "string",
  "severity": "info|warning|blocker",
  "source": "qa_rule|preflight|system_pass|manual",
  "status": "open|in_review|resolved|dismissed",
  "resolved_by": "usr_...|null",
  "resolved_at": "ISO-8601|null",
  "created_at": "ISO-8601",
  "updated_at": "ISO-8601",
  "version": integer,
  "metadata": {}
}
```

### 6.12 Signal

```
{
  "id": "sig_...",
  "workspace_id": "ws_...",
  "batch_id": "bat_...",
  "record_id": "string",
  "field_key": "string",
  "signal_type": "string",
  "severity": "info|warning|blocking",
  "rule_id": "string|null",
  "message": "string",
  "created_at": "ISO-8601",
  "metadata": {}
}
```

### 6.13 Selection Capture

```
{
  "id": "sel_...",
  "workspace_id": "ws_...",
  "author_id": "usr_...",
  "document_id": "doc_...",
  "field_id": "string|null",
  "rfi_id": "rfi_...|null",
  "page_number": integer|null,
  "coordinates": {},             // Bounding box or text range
  "selected_text": "string|null",
  "purpose": "evidence|annotation|rfi_anchor",
  "created_at": "ISO-8601",
  "metadata": {}
}
```

### 6.14 Audit Event (Append-Only)

```
{
  "id": "aud_...",
  "workspace_id": "ws_...",
  "event_type": "string",        // See event type table below
  "actor_id": "usr_...",
  "actor_role": "analyst|verifier|admin|architect",
  "timestamp_iso": "ISO-8601",
  "dataset_id": "string|null",
  "batch_id": "bat_...|null",
  "record_id": "string|null",
  "field_key": "string|null",
  "patch_id": "pat_...|null",
  "before_value": "string|null",
  "after_value": "string|null",
  "metadata": {}
}
```

**Append-only constraint:** No UPDATE or DELETE operations on audit_events. Corrections are new events referencing prior event IDs.

---

## 7. Patch Status Transition Matrix (10 Visible + 2 Hidden)

Source: `ui/viewer/index.html:11783-11796`, role docs

| From → To | Required Role | Self-Approval Allowed | Notes |
|-----------|--------------|----------------------|-------|
| Draft → Submitted | Analyst (author) | N/A | Author submits own patch |
| Submitted → Needs_Clarification | Verifier | Yes | Verifier requests info |
| Submitted → Verifier_Approved | Verifier | **No** | Cannot approve own patch |
| Submitted → Rejected | Verifier/Admin | Yes | Can reject own if needed |
| Needs_Clarification → Verifier_Responded | Analyst (author) | N/A | Author responds |
| Verifier_Responded → Verifier_Approved | Verifier | **No** | Cannot approve own patch |
| Verifier_Responded → Needs_Clarification | Verifier | Yes | Re-request clarification |
| Verifier_Responded → Rejected | Verifier/Admin | Yes | Rejection allowed |
| Verifier_Approved → Admin_Approved | Admin | **No** | Cannot approve own patch |
| Verifier_Approved → Admin_Hold | Admin | Yes | Admin holds for review |
| Admin_Hold → Admin_Approved | Admin | **No** | Release from hold |
| Admin_Hold → Rejected | Admin | Yes | Reject from hold |
| Admin_Approved → Applied | Admin | Yes | Apply to baseline |
| Admin_Approved → Sent_to_Kiwi | Admin | Yes | Export for external processing (hidden) |
| Sent_to_Kiwi → Kiwi_Returned | System/Admin | N/A | Returned from external processing (hidden) |
| Kiwi_Returned → Admin_Approved | Admin | Yes | Re-enter governance flow |
| Kiwi_Returned → Rejected | Admin | Yes | Reject after external review |
| Any active → Cancelled | Analyst (author) | N/A | Author cancels own patch |

---

## 8. Endpoint Catalog

All endpoints under `/api/v2.5/`.

### Health
| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Server health and DB connectivity |

### Workspaces
| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspaces` | List workspaces |
| POST | `/workspaces` | Create workspace |
| GET | `/workspaces/{id}` | Get workspace |
| PATCH | `/workspaces/{id}` | Update workspace (mode, name) |

### Batches
| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspaces/{ws_id}/batches` | List batches in workspace |
| POST | `/workspaces/{ws_id}/batches` | Create batch |
| GET | `/batches/{id}` | Get batch |
| PATCH | `/batches/{id}` | Update batch |

### Accounts
| Method | Path | Description |
|--------|------|-------------|
| GET | `/batches/{bat_id}/accounts` | List accounts in batch |
| POST | `/batches/{bat_id}/accounts` | Create account |
| GET | `/accounts/{id}` | Get account |
| PATCH | `/accounts/{id}` | Update account |

### Contracts
| Method | Path | Description |
|--------|------|-------------|
| GET | `/batches/{bat_id}/contracts` | List contracts in batch |
| POST | `/batches/{bat_id}/contracts` | Create contract |
| GET | `/contracts/{id}` | Get contract |
| PATCH | `/contracts/{id}` | Update contract |

### Documents
| Method | Path | Description |
|--------|------|-------------|
| GET | `/contracts/{ctr_id}/documents` | List documents in contract |
| POST | `/contracts/{ctr_id}/documents` | Create document |
| GET | `/documents/{id}` | Get document |
| PATCH | `/documents/{id}` | Update document |

### Patches
| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspaces/{ws_id}/patches` | List patches (filterable by status, author) |
| POST | `/workspaces/{ws_id}/patches` | Create patch (Draft) |
| GET | `/patches/{id}` | Get patch with history |
| PATCH | `/patches/{id}` | Update patch (status transition or field update) |

### Evidence Packs
| Method | Path | Description |
|--------|------|-------------|
| GET | `/patches/{pat_id}/evidence-packs` | List evidence packs for patch |
| POST | `/patches/{pat_id}/evidence-packs` | Create evidence pack |
| GET | `/evidence-packs/{id}` | Get evidence pack |
| PATCH | `/evidence-packs/{id}` | Update evidence pack blocks |

### Annotations
| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspaces/{ws_id}/annotations` | List annotations |
| POST | `/workspaces/{ws_id}/annotations` | Create annotation |
| GET | `/annotations/{id}` | Get annotation |
| PATCH | `/annotations/{id}` | Update annotation |

### RFIs
| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspaces/{ws_id}/rfis` | List RFIs |
| POST | `/workspaces/{ws_id}/rfis` | Create RFI |
| GET | `/rfis/{id}` | Get RFI |
| PATCH | `/rfis/{id}` | Update RFI (respond, close) |

### Triage Items
| Method | Path | Description |
|--------|------|-------------|
| GET | `/batches/{bat_id}/triage-items` | List triage items |
| POST | `/batches/{bat_id}/triage-items` | Create triage item |
| GET | `/triage-items/{id}` | Get triage item |
| PATCH | `/triage-items/{id}` | Update triage item (resolve, dismiss) |

### Signals
| Method | Path | Description |
|--------|------|-------------|
| GET | `/batches/{bat_id}/signals` | List signals |
| POST | `/batches/{bat_id}/signals` | Create signal |
| GET | `/signals/{id}` | Get signal |

### Selection Captures
| Method | Path | Description |
|--------|------|-------------|
| GET | `/documents/{doc_id}/selection-captures` | List selection captures |
| POST | `/documents/{doc_id}/selection-captures` | Create selection capture |
| GET | `/selection-captures/{id}` | Get selection capture |

### Audit Events (Read-Only via API)
| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspaces/{ws_id}/audit-events` | List audit events (filterable) |
| GET | `/audit-events/{id}` | Get single audit event |

### SSE Event Stream
| Method | Path | Description |
|--------|------|-------------|
| GET | `/workspaces/{ws_id}/events/stream` | SSE stream for real-time events |

---

## 9. Concurrency and Idempotency

### Optimistic Concurrency (PATCH)

Every mutable resource has a `version` integer field (starts at 1, increments on each write).

PATCH requests must include `"version": N` in the body. If the current DB version differs, the server returns:

```
HTTP 409
{
  "error": {
    "code": "STALE_VERSION",
    "message": "Resource has been modified",
    "details": { "current_version": 5, "provided_version": 3 }
  }
}
```

### Idempotency (POST)

POST requests may include an `Idempotency-Key` header. If a request with the same key was previously processed:
- Same payload: return the original response (200, not 201)
- Different payload: return 409 `DUPLICATE_RESOURCE`

Idempotency keys expire after 24 hours.

---

## 10. Audit Event Types

Carried forward from V2.3 (`docs/AUDIT_LOG.md`) with server-side emission:

| Event Type | Trigger |
|------------|---------|
| `PATCH_SUBMITTED` | Patch transitions to Submitted |
| `PATCH_REQUEST_SUBMITTED` | Patch request created |
| `VERIFIER_APPROVED` | Verifier approves patch |
| `ADMIN_APPROVED` | Admin approves patch |
| `PATCH_ADMIN_PROMOTED` | Admin promotes patch to baseline |
| `PATCH_REJECTED` | Patch rejected |
| `PATCH_CANCELLED` | Patch cancelled by author |
| `CLARIFICATION_REQUESTED` | Verifier requests clarification |
| `CLARIFICATION_RESPONDED` | Analyst responds to clarification |
| `FIELD_VERIFIED` | Field marked as verified |
| `FIELD_BLACKLISTED` | Field flagged for blacklist |
| `FIELD_CORRECTED` | Verifier rejects/corrects a field |
| `EVIDENCE_PACK_CREATED` | Evidence pack created |
| `EVIDENCE_PACK_UPDATED` | Evidence pack blocks updated |
| `RFI_CREATED` | RFI opened |
| `RFI_RESPONDED` | RFI responded to |
| `RFI_CLOSED` | RFI closed |
| `ANNOTATION_CREATED` | Annotation added |
| `SELECTION_CAPTURED` | PDF selection captured |
| `BATCH_CREATED` | Batch created |
| `WORKSPACE_CREATED` | Workspace created |
| `WORKSPACE_MODE_CHANGED` | Workspace mode switched |
| `ROLLBACK_CREATED` | Rollback artifact created |
| `ROLLBACK_APPLIED` | Rollback applied |
| `UNKNOWN_COLUMN_DETECTED` | Unknown column routed to triage |

---

## 11. SSE Event Envelope

```json
{
  "event_id": "aud_...",
  "event_type": "PATCH_SUBMITTED",
  "workspace_id": "ws_...",
  "actor_id": "usr_...",
  "actor_role": "analyst",
  "timestamp_iso": "2026-02-12T00:00:00Z",
  "resource_type": "patch",
  "resource_id": "pat_...",
  "payload": { ... }
}
```

SSE stream uses standard `text/event-stream` format with `event:` and `data:` fields. Clients reconnect with `Last-Event-ID` header for resumption.

---

## 12. Google Drive Data Source

### 12.1 Overview

Google Drive is a first-class data source alongside local file upload. Users can connect their Google Drive, browse shared drives/folders, import contract workbooks as working copies, and export governed artifacts back to Drive with status-based naming conventions.

### 12.2 ID Prefix

| Prefix | Resource | Example |
|--------|----------|---------|
| `drv_` | Drive Import Provenance | `drv_01HXYZ...` |

### 12.3 Endpoints

All Drive endpoints are workspace-scoped: `/api/v2.5/workspaces/{workspace_id}/drive/...`

| Method | Path | Description | Auth |
|--------|------|-------------|------|
| POST | `/drive/connect` | Initiate Drive OAuth flow | Admin/Architect |
| POST | `/drive/callback` | Handle OAuth callback, store tokens | Admin/Architect |
| DELETE | `/drive/disconnect` | Revoke Drive access, clear tokens | Admin/Architect |
| GET | `/drive/status` | Check connection state | Any role |
| GET | `/drive/browse` | List drives/folders/files | Any role |
| POST | `/drive/import` | Import file as working copy | Any role |
| POST | `/drive/export` | Export working copy to Drive | Role-based |

### 12.4 Import Semantics

- Import always creates an **immutable source snapshot** (provenance metadata) and an **editable working copy**
- Source file on Drive is never modified by import
- Provenance metadata tracks: `source_file_id`, `source_drive_id`, `source_version`, `imported_at`, `imported_by`, `has_external_modifications`, `baseline_unknown`
- Working copy enters the same pipeline as local upload (parseUnifiedWorkbook → signals → triage)
- Files with pre-existing red cells are accepted; `has_external_modifications` is flagged true

### 12.5 Export Semantics

Two export modes:
- **Save In Progress**: Creates `[IN_PROGRESS-{ROLE}] filename.xlsx` — any role can save
- **Export Final**: Creates `[{STATUS}] filename.xlsx` — role-based naming:
  - `[ANALYST_DONE]` — Analyst marks complete
  - `[VERIFIER_DONE]` — Verifier approved
  - `[ADMIN_FINAL]` — Admin signed off
  - `[REJECTED]` — Rejected at any stage

Export never silently overwrites the source file. A new file or versioned name is always created.

### 12.6 Drive Audit Events

| Event Type | Trigger | Key Metadata |
|------------|---------|--------------|
| `DRIVE_CONNECTED` | OAuth flow completed | `drive_email`, `scopes_granted` |
| `DRIVE_DISCONNECTED` | User disconnects | `drive_email` |
| `DRIVE_FILE_BROWSED` | Folder navigation | `folder_id`, `drive_id` |
| `DRIVE_FILE_IMPORTED` | File imported | `source_file_id`, `filename`, `has_external_modifications` |
| `DRIVE_EXPORT_SAVED` | Save In Progress | `drive_file_id`, `export_filename`, `export_type` |
| `DRIVE_EXPORT_FINALIZED` | Export Final | `drive_file_id`, `export_filename`, `export_type`, `status_label` |

All Drive audit events include `actor_id`, `actor_role`, `effective_role`, `workspace_id`, and sandbox metadata where applicable.

### 12.7 Database Schema (Preview)

**`drive_connections`** — One per workspace, stores OAuth tokens server-side.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `TEXT PK` | `drc_` prefixed ULID |
| `workspace_id` | `TEXT FK` | References workspaces |
| `user_id` | `TEXT FK` | Who connected |
| `drive_email` | `TEXT` | Google account email |
| `access_token` | `TEXT` | Encrypted |
| `refresh_token` | `TEXT` | Encrypted |
| `token_expiry` | `TIMESTAMPTZ` | When access token expires |
| `scopes` | `TEXT` | Granted scopes |
| `status` | `TEXT` | `active` / `revoked` |
| `connected_at` | `TIMESTAMPTZ` | |
| `disconnected_at` | `TIMESTAMPTZ` | Nullable |

**`drive_import_provenance`** — One per imported file, tracks source lineage.

| Column | Type | Notes |
|--------|------|-------|
| `id` | `TEXT PK` | `drv_` prefixed ULID |
| `workspace_id` | `TEXT FK` | References workspaces |
| `batch_id` | `TEXT FK` | Nullable, references batches |
| `source_file_id` | `TEXT` | Google Drive file ID |
| `source_drive_id` | `TEXT` | Nullable (shared drive ID) |
| `source_filename` | `TEXT` | Original filename |
| `source_mime_type` | `TEXT` | MIME type |
| `source_version` | `TEXT` | Nullable (Drive file version) |
| `source_size_bytes` | `INTEGER` | File size |
| `imported_at` | `TIMESTAMPTZ` | |
| `imported_by` | `TEXT FK` | References users |
| `has_external_modifications` | `BOOLEAN` | Pre-existing red cells detected |
| `baseline_unknown` | `BOOLEAN` | No prior baseline in system |

### 12.8 OAuth Scopes Policy

- **Preferred scope**: `https://www.googleapis.com/auth/drive.file` (least privilege — only files created/opened by app)
- **Alternative scope**: `https://www.googleapis.com/auth/drive.readonly` (broader read access for shared folder browsing)
- Drive OAuth is **separate** from login OAuth (different consent flow, different scopes)
- Tokens stored **server-side only** — never in browser storage
- Access tokens auto-refreshed via refresh token before expiry

---

## 13. Cross-References

- `docs/handoff/V25_READINESS_REPORT.md` — Gap analysis
- `docs/decisions/DECISION_V25_DB.md` — PostgreSQL lock
- `docs/decisions/DECISION_V25_DRIVE_SCOPE.md` — Drive scope decisions
- `docs/features/V25_GOOGLE_DRIVE_INTEGRATION.md` — Drive feature specification
- `docs/handoff/V25_DRIVE_READINESS_REPORT.md` — Drive readiness assessment
- `docs/handoff/V25_DRIVE_TASK_LIST.md` — Drive implementation task list
- `docs/memos/V23_ID_MODEL.md` — V2.3 ID model (fingerprint source)
- `docs/memos/V23_GATE_DECISIONS.md` — Gate rules to preserve
- `docs/AUDIT_LOG.md` — V2.3 audit event schema
- `docs/ui/roles/*.md` — Role definitions
- `docs/INTERFACES.md` — Current artifact store interface
