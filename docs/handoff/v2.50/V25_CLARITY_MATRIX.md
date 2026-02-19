# V2.5 Clarity Matrix

**Version:** 1.0
**Date:** 2026-02-12
**Status:** Resolved — All blocking questions answered

---

## Purpose

This document tracks all ambiguities, contradictions, and open questions identified during Gate 1 documentation. Each item is resolved with a canonical decision, resolution source, and impact on downstream tasks.

---

## Blocking Questions (Gate 2 Required)

| # | Question | Status | Resolution Source | Canonical Decision | Impact |
|---|----------|--------|------------------|-------------------|--------|
| Q1 | Authentication mechanism | **Resolved** | User decision (Gate 2) | Dual-mode auth: Google OAuth (OIDC) for production human users; scoped API keys for sandbox and service ingestion | Auth middleware design, endpoint policy, security scheme definitions |
| Q2 | Multi-workspace isolation | **Resolved** | User decision (Gate 2) | Single Postgres DB with strict `workspace_id` scoping. Schema-per-workspace is out of scope for v2.5 | Migration design, query patterns, RLS policy, index strategy |

---

## Non-Blocking Questions (Proposed Defaults — Accepted)

| # | Question | Status | Default | Rationale |
|---|----------|--------|---------|-----------|
| Q3 | Pagination model | **Accepted** | Cursor-based, 50 items default, 200 max | Standard for sorted, append-heavy tables |
| Q4 | Rate limiting | **Deferred** | Not in v2.5 scope | Can be added as middleware later without schema changes |
| Q5 | File/blob storage for evidence PDFs | **Accepted** | URL references only; no blob store in v2.5 | Aligns with current PDF proxy architecture |
| Q6 | Soft-delete vs hard-delete | **Accepted** | Soft-delete (`deleted_at` timestamp) for governed resources | Required for audit trail integrity |

---

## Contradictions Identified and Resolved

### CR1: Patch Status Enum Completeness

**Contradiction:** Gate 1 readiness report listed 11 statuses, but `PATCH_REQUEST_STATUSES` array at `ui/viewer/index.html:11783-11796` has 10 visible + 2 commented-out hidden statuses (Sent_to_Kiwi, Kiwi_Returned). The canonical spec initially omitted Kiwi_Returned.

**Resolution:** All specs now consistently define 12 statuses: 10 visible + 2 hidden (Sent_to_Kiwi, Kiwi_Returned). Hidden statuses are supported in the API but not surfaced in default UI views. The transition matrix includes all 12 statuses.

**Files updated:** `docs/api/API_SPEC_V2_5_CANONICAL.md`, `docs/api/openapi.yaml`, `docs/handoff/V25_READINESS_REPORT.md`

### CR2: Resource Count Definition

**Contradiction:** "14 resources" was stated but the exact list varied across documents.

**Resolution:** 14 primary resources explicitly enumerated: Workspace, Batch, Account, Contract, Document, Patch, Evidence Pack, Annotation, RFI, Triage Item, Signal, Selection Capture, Audit Event, User. Plus 1 join table (Annotation Link). User is authentication-managed, not CRUD-exposed via standard resource endpoints.

**Files updated:** `docs/api/API_SPEC_V2_5_CANONICAL.md` (Section 1)

### CR3: ID Model Coexistence

**Contradiction:** V2.3 uses hash-based IDs as primary identifiers; V2.5 requires ULID-like primaries.

**Resolution:** Both coexist permanently. ULID-like IDs are canonical primaries for all API operations. V2.3 hash-based IDs are preserved as `_fingerprint` columns (indexed, immutable once set). UI can display either; API requests/responses use ULID IDs. Fingerprints are used for deduplication and backward compatibility.

**Files updated:** `docs/handoff/V25_READINESS_REPORT.md` (Conflict C1), `docs/api/API_SPEC_V2_5_CANONICAL.md` (Section 3)

---

## Auth Policy Detail (Q1 Resolution)

### Endpoint Classification

| Category | Auth Required | Token Type | Examples |
|----------|--------------|-----------|----------|
| **Human-governed** | Google OAuth (OIDC) user token | Bearer token (JWT) | PATCH /patches/{id}, POST /patches, POST /annotations, PATCH /rfis/{id} |
| **Service ingestion** | Scoped API key | `X-API-Key` header | POST /signals, POST /triage-items, POST /batches (bulk ingest) |
| **Read endpoints** | Either token type | Bearer or API key | GET /patches, GET /audit-events, GET /workspaces |
| **Health/system** | None | N/A | GET /health |

### API Key Scoping

- API keys are workspace-scoped: each key is bound to exactly one `workspace_id`
- Keys carry explicit scopes (e.g., `signals:write`, `batches:write`, `read:all`)
- Key metadata: `key_id`, `workspace_id`, `scopes[]`, `created_by` (usr_), `created_at`, `expires_at`, `last_used_at`
- Keys are stored hashed (bcrypt or SHA-256 with salt); only the prefix is visible after creation
- Revocation is immediate and audited

### OAuth Flow

1. Client redirects to Google OAuth consent screen
2. Google returns authorization code
3. Server exchanges code for ID token (OIDC)
4. Server validates ID token, extracts email
5. Server resolves email to `usr_` ID and workspace roles from `user_workspace_roles` table
6. Server issues session token (JWT, 1h expiry, refresh via /auth/refresh)
7. All subsequent requests include `Authorization: Bearer {token}`

---

## Workspace Isolation Detail (Q2 Resolution)

### Scoping Rules

1. `workspace_id` is a **required foreign key** on all governed resource tables (batches, accounts, contracts, documents, patches, evidence_packs, annotations, rfis, triage_items, signals, selection_captures, audit_events)
2. Every query includes `WHERE workspace_id = :ws_id` — enforced at the repository layer, not optional
3. Cross-workspace queries are architecturally forbidden; no endpoint accepts multiple workspace IDs
4. API key scoping: each API key is bound to exactly one workspace

### Database Enforcement

- **FK constraint:** `workspace_id REFERENCES workspaces(id)` on all resource tables
- **Composite indexes:** All query-critical indexes include `workspace_id` as the leading column
- **RLS policy (optional hardening):** `CREATE POLICY workspace_isolation ON {table} USING (workspace_id = current_setting('app.workspace_id')::text)`
- **Server middleware:** Sets `app.workspace_id` session variable from authenticated context before any query

### What's Out of Scope

- Schema-per-workspace isolation
- Cross-workspace data sharing or federation
- Workspace archival or deletion (soft-delete only in v2.5)
- Multi-region workspace placement
