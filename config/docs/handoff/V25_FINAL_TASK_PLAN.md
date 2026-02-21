# V2.5 Final Task Plan

**Version:** 1.0
**Date:** 2026-02-12
**Status:** Gate 3 — Frozen
**Prerequisite:** Gates 1 (Docs) and 2 (Clarity) complete and approved

---

## Purpose

This document is the frozen implementation plan for API v2.5. All task IDs, acceptance criteria, sequencing, and dependencies are locked. No tasks may be added, removed, or reordered without a formal Change Request per `docs/handoff/V25_LOCKED_DECISIONS.md`.

---

## Implementation Phases

```
Phase 1: Persistence Foundation (V25-100 → V25-106)
  ├── V25-100 DB Provisioning
  ├── V25-101 Migration Framework ──→ V25-102 Core Tables ──→ V25-103 Seed Fixtures
  ├── V25-104 DB Connection Layer
  ├── V25-105 ULID Generator
  └── V25-106 Health Endpoint ──→ Phase 2

Phase 2: API Implementation (V25-110 → V25-135)
  ├── V25-110 Workspace CRUD ──→ V25-111 Batch CRUD ──→ V25-112 Contract/Document CRUD
  │                                                   ├── V25-113 Account CRUD
  │                                                   ├── V25-118 Triage Item CRUD
  │                                                   ├── V25-119 Signal CRUD
  │                                                   └── V25-114 Patch CRUD ──→ V25-115 Evidence Pack CRUD
  │                                                                           ├── V25-117 RFI CRUD
  │                                                                           └── V25-131 Self-Approval Gate
  ├── V25-116 Annotation CRUD (depends on V25-110)
  ├── V25-120 Selection Capture CRUD (depends on V25-112)
  ├── V25-121 Audit Event Read API (depends on V25-110)
  ├── V25-130 RBAC Middleware (depends on V25-110)
  ├── V25-132 Optimistic Concurrency (depends on V25-110)
  ├── V25-133 Idempotency Keys (depends on V25-110)
  ├── V25-134 Audit Event Emission (depends on V25-106)
  └── V25-135 SSE Event Stream (depends on V25-134)

Phase 3: UI Integration (V25-140 → V25-142)
  ├── V25-140 Workspace Mode Wire (depends on V25-110)
  ├── V25-141 Audit Data Flow (depends on V25-121, V25-135)
  └── V25-142 Selection Capture Path (depends on V25-120)

Phase 4: Audit & Verification (V25-200 → V25-201)
  ├── V25-200 Compliance Audit (depends on Gate 4 complete)
  └── V25-201 Smoke Tests (depends on V25-200)
```

---

## Phase 1: Persistence Foundation

### V25-100: Database Provisioning

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | Gate 3 approved |
| **Estimated effort** | XS |

**Acceptance Criteria:**
1. PostgreSQL database provisioned via Replit built-in tooling
2. `DATABASE_URL` environment variable available and connecting successfully
3. Connection verified by a simple `SELECT 1` query logged at startup
4. No manual DSN or credentials hardcoded anywhere

---

### V25-101: Migration Framework

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | V25-100 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. `server/migrations/` directory created with numbered `.sql` files
2. Python migration runner in `server/migrate.py` that:
   - Reads all `NNN_*.sql` files in order
   - Tracks applied migrations in a `schema_migrations` table
   - Skips already-applied migrations
   - Runs automatically on server startup (before accepting requests)
   - Logs each migration applied
3. Runner is idempotent — re-running is safe
4. No ORM dependency — plain SQL via psycopg2/asyncpg

---

### V25-102: Core Tables Migration

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | V25-101 |
| **Estimated effort** | L |

**Acceptance Criteria:**
1. Migration file `001_core_tables.sql` creates all tables per canonical spec Section 6:
   - `workspaces` (id, name, mode, created_at, updated_at, version, metadata)
   - `batches` (id, workspace_id FK, name, source, batch_fingerprint, status, record_count, timestamps, version, metadata)
   - `accounts` (id, batch_id FK, workspace_id FK, account_name, billing_country, billing_city, account_fingerprint, timestamps, version, metadata)
   - `contracts` (id, batch_id FK, account_id FK nullable, workspace_id FK, contract_fingerprint, contract_id_source, file_url, file_name, status, health_score, timestamps, version, metadata)
   - `documents` (id, contract_id FK, batch_id FK, workspace_id FK, document_fingerprint, file_url, file_name, section_name, timestamps, version, metadata)
   - `patches` (id, workspace_id FK, batch_id FK, record_id, field_key, author_id FK, status, intent, when_clause JSONB, then_clause JSONB, because_clause, evidence_pack_id nullable, submitted_at, resolved_at, file_name, file_url, before_value, after_value, history JSONB, timestamps, version, metadata)
   - `evidence_packs` (id, patch_id FK, workspace_id FK, author_id FK, blocks JSONB, status, timestamps, version, metadata)
   - `annotations` (id, workspace_id FK, author_id FK, target_type, target_id, content, annotation_type, timestamps, version, metadata)
   - `annotation_links` (id, annotation_id FK, linked_type, linked_id, created_at)
   - `rfis` (id, workspace_id FK, patch_id FK nullable, author_id FK, target_record_id, target_field_key, question, response, responder_id nullable, status, timestamps, version, metadata)
   - `triage_items` (id, workspace_id FK, batch_id FK, record_id, field_key, issue_type, severity, source, status, resolved_by, resolved_at, timestamps, version, metadata)
   - `signals` (id, workspace_id FK, batch_id FK, record_id, field_key, signal_type, severity, rule_id, message, created_at, metadata)
   - `selection_captures` (id, workspace_id FK, author_id FK, document_id FK, field_id, rfi_id nullable, page_number, coordinates JSONB, selected_text, purpose, created_at, metadata)
   - `audit_events` (id, workspace_id FK, event_type, actor_id, actor_role, timestamp_iso, dataset_id, batch_id, record_id, field_key, patch_id, before_value, after_value, metadata)
   - `users` (id, email, display_name, avatar_url, created_at, updated_at)
   - `user_workspace_roles` (user_id FK, workspace_id FK, role, granted_at, granted_by)
   - `api_keys` (key_id, workspace_id FK, key_hash, key_prefix, scopes JSONB, created_by FK, created_at, expires_at, last_used_at, revoked_at)
   - `idempotency_keys` (key_hash PK, workspace_id FK, endpoint, response JSONB, created_at, expires_at)
2. All tables use `TEXT` primary key columns for ULID-prefixed IDs
3. `workspace_id` is a leading column in composite indexes on all governed tables
4. `audit_events` has a trigger or policy preventing UPDATE and DELETE
5. `_fingerprint` columns are indexed for dedup lookups
6. `deleted_at TIMESTAMPTZ` column on all soft-deletable tables (all except audit_events, users, user_workspace_roles, api_keys, idempotency_keys)
7. `version INTEGER NOT NULL DEFAULT 1` on all mutable resources
8. Migration applies cleanly on a fresh database

---

### V25-103: Seed Fixtures

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | BE |
| **Dependencies** | V25-102 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. Migration file `002_seed_fixtures.sql` with deterministic dev data:
   - 1 workspace (`ws_SEED01...`, name: "Demo Workspace", mode: "sandbox")
   - 4 users (analyst, verifier, admin, architect) with `usr_SEED` prefixed IDs
   - 4 `user_workspace_roles` entries matching above
   - 1 batch with 2 accounts, 2 contracts, 3 documents
   - 2 patches in different statuses (Draft, Submitted)
   - 1 evidence pack
   - 2 triage items, 2 signals
2. All seed IDs use `_SEED` prefix for easy identification
3. Seed data is safe to re-run (uses `INSERT ... ON CONFLICT DO NOTHING`)
4. Seed data only applies when `SEED_DATA=true` env var is set

---

### V25-104: Database Connection Layer

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | V25-100 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. `server/db.py` module with:
   - Connection pool initialization from `DATABASE_URL`
   - `get_db()` async context manager for request-scoped connections
   - Graceful shutdown that drains pool
   - Connection health check method
2. Pool configured with reasonable defaults (min=2, max=10)
3. All database access goes through this layer — no direct connection creation elsewhere
4. Connection errors raise clear, loggable exceptions

---

### V25-105: ULID ID Generator

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | None |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. `server/ulid.py` module with `generate_id(prefix: str) -> str` function
2. Returns format: `{prefix}_{timestamp_b32}{random_b32}` (26 chars after prefix)
3. Supports all 14 prefixes: `ws_`, `bat_`, `acc_`, `ctr_`, `doc_`, `pat_`, `evp_`, `sig_`, `tri_`, `aud_`, `rfi_`, `ann_`, `sel_`, `usr_`
4. Timestamp component is Crockford Base32 encoded milliseconds (10 chars)
5. Random component is Crockford Base32 encoded random bytes (16 chars)
6. IDs are lexicographically sortable by creation time
7. No external ULID library dependency — Python standard library only

---

### V25-106: Health Endpoint

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | V25-104 |
| **Estimated effort** | XS |

**Acceptance Criteria:**
1. `GET /api/v2.5/health` returns:
   ```json
   { "status": "ok", "db": "connected", "version": "2.5.0" }
   ```
2. If DB connection fails: `{ "status": "degraded", "db": "disconnected", "version": "2.5.0" }` with HTTP 503
3. No authentication required
4. Response time < 200ms under normal conditions

---

## Phase 2: API Implementation

### V25-110: Workspace CRUD

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | V25-106 |
| **Estimated effort** | M |

**Acceptance Criteria:**
1. Endpoints per canonical spec Section 8:
   - `GET /api/v2.5/workspaces` — list with cursor pagination
   - `POST /api/v2.5/workspaces` — create with response envelope
   - `GET /api/v2.5/workspaces/{id}` — get by ID
   - `PATCH /api/v2.5/workspaces/{id}` — update (name, mode) with optimistic concurrency
2. Standard response envelope on all responses (data + meta)
3. Standard error envelope on all errors
4. PATCH enforces version check (409 STALE_VERSION on mismatch)
5. POST supports `Idempotency-Key` header
6. Establishes the repository pattern used by all subsequent CRUD tasks

---

### V25-111: Batch CRUD

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | V25-110 |
| **Estimated effort** | M |

**Acceptance Criteria:**
1. Endpoints per canonical spec:
   - `GET /api/v2.5/workspaces/{ws_id}/batches` — list with workspace scoping
   - `POST /api/v2.5/workspaces/{ws_id}/batches` — create
   - `GET /api/v2.5/batches/{id}` — get by ID (verifies workspace_id match)
   - `PATCH /api/v2.5/batches/{id}` — update with optimistic concurrency
2. All queries filter by `workspace_id`
3. Soft-delete support (`deleted_at` filtering, `?include_deleted=true`)
4. `batch_fingerprint` indexed for dedup lookup

---

### V25-112: Contract + Document CRUD

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | BE |
| **Dependencies** | V25-111 |
| **Estimated effort** | M |

**Acceptance Criteria:**
1. Contract endpoints:
   - `GET /api/v2.5/batches/{bat_id}/contracts` — list
   - `POST /api/v2.5/batches/{bat_id}/contracts` — create
   - `GET /api/v2.5/contracts/{id}` — get
   - `PATCH /api/v2.5/contracts/{id}` — update
2. Document endpoints:
   - `GET /api/v2.5/contracts/{ctr_id}/documents` — list
   - `POST /api/v2.5/contracts/{ctr_id}/documents` — create
   - `GET /api/v2.5/documents/{id}` — get
   - `PATCH /api/v2.5/documents/{id}` — update
3. `contract_fingerprint` and `document_fingerprint` indexed
4. Workspace scoping enforced on all queries

---

### V25-113: Account CRUD

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | BE |
| **Dependencies** | V25-111 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. Endpoints per canonical spec:
   - `GET /api/v2.5/batches/{bat_id}/accounts` — list
   - `POST /api/v2.5/batches/{bat_id}/accounts` — create
   - `GET /api/v2.5/accounts/{id}` — get
   - `PATCH /api/v2.5/accounts/{id}` — update
2. `account_fingerprint` indexed for dedup
3. Workspace scoping enforced

---

### V25-114: Patch CRUD + Transition Matrix

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | V25-111 |
| **Estimated effort** | L |

**Acceptance Criteria:**
1. Endpoints per canonical spec:
   - `GET /api/v2.5/workspaces/{ws_id}/patches` — list with filters (status, author_id, batch_id)
   - `POST /api/v2.5/workspaces/{ws_id}/patches` — create (always as Draft)
   - `GET /api/v2.5/patches/{id}` — get with full history
   - `PATCH /api/v2.5/patches/{id}` — update fields OR status transition
2. Full transition matrix from canonical spec Section 7 enforced:
   - Valid transitions checked against source → target status pairs
   - Role requirements checked (Analyst, Verifier, Admin per matrix)
   - Invalid transitions return 409 `INVALID_TRANSITION`
3. Status transition appends to `history` array with actor, timestamp, from_status, to_status
4. `submitted_at` set on first transition to Submitted
5. `resolved_at` set on transition to Applied, Rejected, or Cancelled
6. Hidden statuses (Sent_to_Kiwi, Kiwi_Returned) excluded from list default; available with `?include_hidden=true`

---

### V25-115: Evidence Pack CRUD

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | BE |
| **Dependencies** | V25-114 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. Endpoints per canonical spec:
   - `GET /api/v2.5/patches/{pat_id}/evidence-packs` — list
   - `POST /api/v2.5/patches/{pat_id}/evidence-packs` — create
   - `GET /api/v2.5/evidence-packs/{id}` — get
   - `PATCH /api/v2.5/evidence-packs/{id}` — update blocks
2. `blocks` stored as JSONB with structured sub-keys (context, data_reference, pdf_anchor, rationale)
3. Status transitions: incomplete → complete (via PATCH)
4. Workspace scoping enforced through patch ownership chain

---

### V25-116: Annotation + Annotation Link CRUD

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | BE |
| **Dependencies** | V25-110 |
| **Estimated effort** | M |

**Acceptance Criteria:**
1. Annotation endpoints:
   - `GET /api/v2.5/workspaces/{ws_id}/annotations` — list with filters (target_type, target_id)
   - `POST /api/v2.5/workspaces/{ws_id}/annotations` — create
   - `GET /api/v2.5/annotations/{id}` — get
   - `PATCH /api/v2.5/annotations/{id}` — update
2. Annotation Link management:
   - Links created/removed via annotation endpoints (nested in annotation payload)
   - `linked_type` constrained to: patch, rfi, evidence_pack, selection_capture
3. `target_type` constrained to: field, record, contract, document
4. `annotation_type` constrained to: note, flag, question

---

### V25-117: RFI CRUD

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | BE |
| **Dependencies** | V25-114 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. Endpoints per canonical spec:
   - `GET /api/v2.5/workspaces/{ws_id}/rfis` — list with filters (status, patch_id)
   - `POST /api/v2.5/workspaces/{ws_id}/rfis` — create
   - `GET /api/v2.5/rfis/{id}` — get
   - `PATCH /api/v2.5/rfis/{id}` — update (respond, close)
2. Status transitions: open → responded → closed
3. `response` and `responder_id` set on transition to responded
4. Optional `patch_id` link for patch-associated RFIs

---

### V25-118: Triage Item CRUD

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | BE |
| **Dependencies** | V25-111 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. Endpoints per canonical spec:
   - `GET /api/v2.5/batches/{bat_id}/triage-items` — list with filters (severity, status, source)
   - `POST /api/v2.5/batches/{bat_id}/triage-items` — create (service ingestion endpoint)
   - `GET /api/v2.5/triage-items/{id}` — get
   - `PATCH /api/v2.5/triage-items/{id}` — update (resolve, dismiss)
2. Status transitions: open → in_review → resolved/dismissed
3. `resolved_by` and `resolved_at` set on resolution
4. `source` constrained to: qa_rule, preflight, system_pass, manual
5. POST accepts scoped API key auth (service ingestion)

---

### V25-119: Signal CRUD

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Owner** | BE |
| **Dependencies** | V25-111 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. Endpoints per canonical spec:
   - `GET /api/v2.5/batches/{bat_id}/signals` — list with filters (severity, signal_type)
   - `POST /api/v2.5/batches/{bat_id}/signals` — create (service ingestion endpoint)
   - `GET /api/v2.5/signals/{id}` — get
2. Signals are immutable after creation — no PATCH endpoint
3. POST accepts scoped API key auth (service ingestion)
4. Workspace scoping enforced

---

### V25-120: Selection Capture CRUD

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Owner** | BE |
| **Dependencies** | V25-112 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. Endpoints per canonical spec:
   - `GET /api/v2.5/documents/{doc_id}/selection-captures` — list
   - `POST /api/v2.5/documents/{doc_id}/selection-captures` — create
   - `GET /api/v2.5/selection-captures/{id}` — get
2. Selection captures are immutable after creation — no PATCH endpoint
3. `coordinates` stored as JSONB (bounding box or text range)
4. `purpose` constrained to: evidence, annotation, rfi_anchor

---

### V25-121: Audit Event Read API

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | BE |
| **Dependencies** | V25-110 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. Endpoints per canonical spec:
   - `GET /api/v2.5/workspaces/{ws_id}/audit-events` — list with filters (event_type, actor_id, batch_id, patch_id, date range)
   - `GET /api/v2.5/audit-events/{id}` — get single event
2. Read-only — no POST, PATCH, or DELETE endpoints
3. Cursor-based pagination (default 50, max 200)
4. Workspace scoping enforced
5. Accepts either Bearer token or scoped API key

---

### V25-130: RBAC Middleware

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | V25-110 |
| **Estimated effort** | M |

**Acceptance Criteria:**
1. FastAPI dependency that resolves authenticated user and workspace role
2. Role resolution from `user_workspace_roles` table
3. Permission check on all mutating endpoints:
   - Analyst: create/edit draft patches, submit, respond to clarification, create evidence/annotations
   - Verifier: all Analyst + approve/reject at verifier gate, request clarification
   - Admin: all Verifier + admin approve/hold/apply, export
   - Architect: all Admin + system config, schema editing
4. Returns 403 `FORBIDDEN` with clear message when role insufficient
5. API key auth resolves to workspace but not a specific user role — scoped by key permissions instead
6. Health endpoint exempted from auth

---

### V25-131: Self-Approval Gate

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | V25-114, V25-130 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. On PATCH to `Verifier_Approved`: reject if `actor_id === patch.author_id` → 403 `SELF_APPROVAL_BLOCKED`
2. On PATCH to `Admin_Approved`: reject if `actor_id === patch.author_id` → 403 `SELF_APPROVAL_BLOCKED`
3. Cannot be overridden by any role including Architect
4. Audit event emitted on blocked attempt
5. Error response includes clear message: "Cannot approve your own patch"

---

### V25-132: Optimistic Concurrency

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | V25-110 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. All PATCH endpoints require `version` in request body
2. Repository layer checks `WHERE id = $1 AND version = $2`
3. If no row updated (version mismatch): 409 `STALE_VERSION` with details `{ current_version, provided_version }`
4. On successful update: `version` incremented by 1
5. Version starts at 1 for new resources

---

### V25-133: Idempotency Keys

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | BE |
| **Dependencies** | V25-110 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. POST endpoints accept optional `Idempotency-Key` header
2. Key + endpoint stored in `idempotency_keys` table with response payload
3. Duplicate key with same payload: return original response (200, not 201)
4. Duplicate key with different payload: 409 `DUPLICATE_RESOURCE`
5. Keys expire after 24 hours
6. Cleanup of expired keys runs periodically (startup + hourly)

---

### V25-134: Audit Event Emission

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | BE |
| **Dependencies** | V25-106 |
| **Estimated effort** | M |

**Acceptance Criteria:**
1. Every mutating API call inserts an `audit_events` row within the same transaction
2. All 25 event types from canonical spec Section 10 supported
3. `actor_id` and `actor_role` captured from authenticated context
4. `before_value` and `after_value` captured for field-level changes
5. Audit insert never fails silently — transaction rolls back if audit fails
6. `audit_events` table enforces append-only (no UPDATE/DELETE)

---

### V25-135: SSE Event Stream

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | BE |
| **Dependencies** | V25-134 |
| **Estimated effort** | M |

**Acceptance Criteria:**
1. `GET /api/v2.5/workspaces/{ws_id}/events/stream` returns `text/event-stream`
2. SSE envelope per canonical spec Section 11:
   ```
   event: PATCH_SUBMITTED
   data: {"event_id":"aud_...","workspace_id":"ws_...","actor_id":"usr_...", ...}
   ```
3. `Last-Event-ID` header supported for resumption
4. Stream is workspace-scoped — only events for the connected workspace
5. Authentication required (Bearer or API key)
6. Graceful handling of client disconnection (no resource leaks)
7. PostgreSQL LISTEN/NOTIFY or polling mechanism for event delivery

---

## Phase 3: UI Integration

### V25-140: Workspace Mode Wire

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | FE |
| **Dependencies** | V25-110 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. UI reads workspace mode from API on load (`GET /workspaces/{id}`)
2. Mode toggle persists via API (`PATCH /workspaces/{id}`)
3. Fallback to localStorage if API unavailable (offline-first preservation)
4. ES5 compliance maintained in all UI changes

---

### V25-141: Audit Timeline Data Flow

| Field | Value |
|-------|-------|
| **Priority** | P1 |
| **Owner** | FE |
| **Dependencies** | V25-121, V25-135 |
| **Estimated effort** | M |

**Acceptance Criteria:**
1. Audit timeline reads from API (`GET /audit-events`) instead of IndexedDB
2. Real-time updates via SSE stream connection
3. Graceful degradation to polling if SSE fails
4. IndexedDB audit store preserved as cache layer (not source of truth)
5. ES5 compliance maintained

---

### V25-142: Selection Capture Path

| Field | Value |
|-------|-------|
| **Priority** | P2 |
| **Owner** | FE |
| **Dependencies** | V25-120 |
| **Estimated effort** | S |

**Acceptance Criteria:**
1. Selection captures persisted via API (`POST /selection-captures`)
2. `field_id` → `selection_id` trace linkage maintained
3. Offline captures queued and synced when API available
4. ES5 compliance maintained

---

## Phase 4: Audit & Verification

### V25-200: Compliance Audit

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | Fullstack |
| **Dependencies** | Gate 4 complete |
| **Estimated effort** | M |

**Acceptance Criteria:**
1. Audit report document with Pass/Fail for each non-negotiable:
   - Resource-based routes (no verb endpoints)
   - PATCH for all transitions
   - ULID primary IDs with correct prefixes
   - Optimistic concurrency (409 STALE_VERSION)
   - No-self-approval server-enforced (403 SELF_APPROVAL_BLOCKED)
   - Append-only audit_events (no UPDATE/DELETE)
   - Postgres canonical (all state in DB, not localStorage)
   - Workspace isolation (workspace_id scoping on all queries)
   - Dual-mode auth (Bearer + API key)
2. Any failures documented with remediation plan

---

### V25-201: Smoke Tests

| Field | Value |
|-------|-------|
| **Priority** | P0 |
| **Owner** | Fullstack |
| **Dependencies** | V25-200 |
| **Estimated effort** | M |

**Acceptance Criteria:**
1. Automated test script (`scripts/v25_smoke.sh` or Python equivalent) that verifies:
   - Health endpoint returns 200 with DB connected
   - Workspace CRUD round-trip (create → read → update → list)
   - Batch CRUD round-trip nested under workspace
   - Patch lifecycle: Draft → Submitted → Verifier_Approved → Admin_Approved → Applied
   - Self-approval blocked (403 on own patch approval)
   - Optimistic concurrency (409 on stale version)
   - Audit events created for each mutation
   - Cursor pagination returns correct structure
   - Error envelopes have correct format
2. All tests pass on fresh database with seed fixtures
3. Tests are idempotent and can be re-run

---

## Execution Sequencing

### Critical Path (P0 — must complete first)

```
V25-100 → V25-101 → V25-102 → V25-104 → V25-106 → V25-110 → V25-111 → V25-114
                                                      ↓
                                               V25-130 (RBAC)
                                               V25-132 (Concurrency)
                                               V25-134 (Audit Emission)
                                                      ↓
                                               V25-131 (Self-Approval)
```

### Parallel Work (after critical path unblocks)

Once V25-111 is complete, these can proceed in parallel:
- V25-112 (Contract/Document) + V25-113 (Account) + V25-118 (Triage) + V25-119 (Signal)

Once V25-114 is complete:
- V25-115 (Evidence Pack) + V25-117 (RFI)

Independent of resource CRUD (after V25-106):
- V25-105 (ULID — no dependencies)
- V25-134 (Audit Emission) → V25-135 (SSE)

### Phase 3 Gate

UI integration tasks (V25-140, V25-141, V25-142) should not begin until their API dependencies are verified working via manual testing.

---

## Effort Legend

| Size | Estimated Scope |
|------|----------------|
| XS | < 1 hour, single file change |
| S | 1-3 hours, 1-2 files |
| M | 3-8 hours, 2-4 files |
| L | 8-16 hours, 4+ files |

---

## Cross-References

- `docs/api/API_SPEC_V2_5_CANONICAL.md` — Schema and endpoint definitions
- `docs/handoff/V25_LOCKED_DECISIONS.md` — Frozen decisions (D1-D11)
- `docs/handoff/V25_CONTRACT_LOCK.md` — What cannot change without CR
- `docs/api/openapi.yaml` — Machine-readable endpoint spec
- `docs/api/asyncapi.yaml` — SSE event definitions
