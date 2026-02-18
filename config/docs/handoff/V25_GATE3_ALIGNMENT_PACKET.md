# V2.5 Gate 3 — Alignment Packet

**Version:** 1.0
**Date:** 2026-02-12
**Status:** Submitted for GO/NO-GO
**Prerequisite:** Gates 1 (Docs) and 2 (Clarity) approved

---

## 1. Final Task Plan

### Summary Table

| Task ID | Priority | Owner | Dependencies | Acceptance Criteria (summary) | Status |
|---------|----------|-------|-------------|-------------------------------|--------|
| V25-100 | P0 | BE | Gate 3 approved | Provision Postgres via Replit; `DATABASE_URL` available; `SELECT 1` verified; no hardcoded creds | Pending |
| V25-101 | P0 | BE | V25-100 | `server/migrations/` with numbered `.sql` files; Python runner tracks `schema_migrations`; idempotent; runs on startup; no ORM | Pending |
| V25-102 | P0 | BE | V25-101 | `001_core_tables.sql` creates all 18 tables per spec Section 6; TEXT PKs for ULIDs; `workspace_id` leading composite indexes; `audit_events` append-only trigger; `_fingerprint` indexes; `deleted_at` on soft-deletable tables; `version DEFAULT 1` on mutable resources | Pending |
| V25-103 | P1 | BE | V25-102 | `002_seed_fixtures.sql` with 1 workspace, 4 users, 4 roles, 1 batch, 2 accounts, 2 contracts, 3 documents, 2 patches, 1 evidence pack, 2 triage items, 2 signals; `_SEED` prefix IDs; `ON CONFLICT DO NOTHING`; gated on `SEED_DATA=true` | Pending |
| V25-104 | P0 | BE | V25-100 | `server/db.py` with connection pool (min 2, max 10); `get_db()` async context manager; graceful shutdown; health check method; all DB access through this layer | Pending |
| V25-105 | P0 | BE | None | `server/ulid.py`; `generate_id(prefix)` → `{prefix}_{26-char}` Crockford Base32; 14 prefixes; lexicographically sortable; stdlib only | Pending |
| V25-106 | P0 | BE | V25-104 | `GET /api/v2.5/health` → `{status,db,version}`; 503 if DB disconnected; no auth; < 200ms | Pending |
| V25-110 | P0 | BE | V25-106 | Workspace CRUD (list/create/get/update); standard envelopes; PATCH with version check (409 STALE_VERSION); idempotency-key on POST; establishes repo pattern | Pending |
| V25-111 | P0 | BE | V25-110 | Batch CRUD nested under workspace; workspace_id scoping; soft-delete; `batch_fingerprint` indexed | Pending |
| V25-112 | P1 | BE | V25-111 | Contract CRUD + Document CRUD nested under parent; `contract_fingerprint` and `document_fingerprint` indexed; workspace scoping | Pending |
| V25-113 | P1 | BE | V25-111 | Account CRUD nested under batch; `account_fingerprint` indexed; workspace scoping | Pending |
| V25-114 | P0 | BE | V25-111 | Patch CRUD + full transition matrix (12 statuses); role requirements per transition; `history` append; `submitted_at`/`resolved_at` set; hidden statuses excluded by default | Pending |
| V25-115 | P1 | BE | V25-114 | Evidence Pack CRUD nested under patch; `blocks` as JSONB; status: incomplete → complete; workspace scoping through patch chain | Pending |
| V25-116 | P1 | BE | V25-110 | Annotation CRUD + Annotation Link management; `target_type` and `annotation_type` constrained; workspace scoping | Pending |
| V25-117 | P1 | BE | V25-114 | RFI CRUD; status: open → responded → closed; `responder_id` set on response; optional `patch_id` link | Pending |
| V25-118 | P1 | BE | V25-111 | Triage Item CRUD; status: open → in_review → resolved/dismissed; `source` constrained; POST accepts API key auth | Pending |
| V25-119 | P2 | BE | V25-111 | Signal CRUD (list/create/get only — immutable, no PATCH); POST accepts API key auth; workspace scoping | Pending |
| V25-120 | P2 | BE | V25-112 | Selection Capture CRUD (list/create/get only — immutable); `coordinates` as JSONB; `purpose` constrained | Pending |
| V25-121 | P1 | BE | V25-110 | Audit Event Read API (list/get only — read-only); filters: event_type, actor_id, batch_id, patch_id, date range; cursor pagination; dual-auth | Pending |
| V25-130 | P0 | BE | V25-110 | RBAC middleware; role resolution from `user_workspace_roles`; Analyst/Verifier/Admin/Architect permissions enforced; 403 FORBIDDEN; API key resolves to workspace scopes; health exempt | Pending |
| V25-131 | P0 | BE | V25-114, V25-130 | Self-approval gate: 403 `SELF_APPROVAL_BLOCKED` on own patch at Verifier_Approved or Admin_Approved; no override; audit event on blocked attempt | Pending |
| V25-132 | P0 | BE | V25-110 | All PATCH requires `version`; repo checks `WHERE version = $v`; 409 STALE_VERSION with `{current_version, provided_version}`; version increments on success | Pending |
| V25-133 | P1 | BE | V25-110 | Idempotency-Key header on POST; stored in `idempotency_keys`; duplicate same payload → original response; duplicate different payload → 409; 24h expiry; periodic cleanup | Pending |
| V25-134 | P0 | BE | V25-106 | Every mutation inserts `audit_events` row in same transaction; 25 event types; actor context captured; before/after values; rollback on audit failure; append-only enforced | Pending |
| V25-135 | P1 | BE | V25-134 | SSE at `/workspaces/{ws_id}/events/stream`; `text/event-stream`; `Last-Event-ID` resumption; workspace-scoped; auth required; graceful disconnect; LISTEN/NOTIFY or polling | Pending |
| V25-140 | P1 | FE | V25-110 | UI reads workspace mode from API; mode toggle persists via PATCH; localStorage fallback if API unavailable; ES5 compliance | Pending |
| V25-141 | P1 | FE | V25-121, V25-135 | Audit timeline reads from API; real-time via SSE; graceful degradation to polling; IndexedDB as cache only; ES5 compliance | Pending |
| V25-142 | P2 | FE | V25-120 | Selection captures persisted via API; `field_id` → `selection_id` trace; offline queue with sync; ES5 compliance | Pending |
| V25-200 | P0 | Fullstack | Gate 4 complete | Compliance audit report: Pass/Fail for each non-negotiable (resource routes, PATCH transitions, ULID IDs, optimistic concurrency, no-self-approval, append-only audit, Postgres canonical, workspace isolation, dual-mode auth); remediation plan for any failures | Pending |
| V25-201 | P0 | Fullstack | V25-200 | Automated smoke test script: health 200, workspace CRUD round-trip, batch CRUD, patch lifecycle Draft→Applied, self-approval blocked 403, stale version 409, audit events emitted, cursor pagination, error envelopes; idempotent; passes on fresh DB with seeds | Pending |

**Totals:** 30 tasks — 14 P0, 10 P1, 4 P2, 2 Gate-5

---

## 2. Sequencing Lock

### Execution Order

**No code is written until Gate 3 GO is issued.** This is a hard gate — no implementation work of any kind begins before formal approval of this alignment packet.

#### Phase 1 — Persistence Foundation (must complete before Phase 2)

```
V25-100 (DB Provisioning)
    ├── V25-101 (Migration Framework)
    │       └── V25-102 (Core Tables)
    │               └── V25-103 (Seed Fixtures)
    ├── V25-104 (DB Connection Layer)
    │       └── V25-106 (Health Endpoint) ──→ GATE to Phase 2
    └── V25-105 (ULID Generator — no deps, parallel)
```

**Phase 1 exit criteria:** Health endpoint returns `{"status":"ok","db":"connected","version":"2.5.0"}` on provisioned Postgres with all 18 tables created.

#### Phase 2 — API Implementation (must complete before Phase 3)

Critical path:
```
V25-110 (Workspace CRUD) → V25-111 (Batch CRUD) → V25-114 (Patch CRUD)
                               ↓
                         V25-130 (RBAC)
                         V25-132 (Concurrency)
                         V25-134 (Audit Emission)
                               ↓
                         V25-131 (Self-Approval Gate)
```

Parallel work after V25-111:
- V25-112 (Contract/Document), V25-113 (Account), V25-118 (Triage), V25-119 (Signal)

Parallel work after V25-114:
- V25-115 (Evidence Pack), V25-117 (RFI)

Independent after V25-106:
- V25-134 (Audit Emission) → V25-135 (SSE)

Independent after V25-110:
- V25-116 (Annotation), V25-121 (Audit Read), V25-133 (Idempotency)

After V25-112:
- V25-120 (Selection Capture)

**Phase 2 exit criteria:** All 14 resource endpoints responding correctly with RBAC, optimistic concurrency, audit emission, and self-approval gate enforced.

#### Phase 3 — UI Integration (must complete before Phase 4)

```
V25-140 (Workspace Mode Wire)     — after V25-110 verified
V25-141 (Audit Timeline Data Flow) — after V25-121 + V25-135 verified
V25-142 (Selection Capture Path)   — after V25-120 verified
```

**Phase 3 exit criteria:** UI reads from and writes to API for workspace mode, audit timeline, and selection captures. ES5 compliance maintained.

#### Phase 4 — Audit & Verification (Gate 5)

```
V25-200 (Compliance Audit) — after all Gate 4 code complete
V25-201 (Smoke Tests)      — after V25-200
```

**Phase 4 exit criteria:** All non-negotiables pass. Automated smoke tests green on fresh DB.

### Explicit No-Code Statement

**No implementation code for API v2.5 will be written, committed, or deployed until this Gate 3 alignment packet receives a formal GO decision.** Gate 3 is a hard prerequisite for Gate 4 (Code). This includes database provisioning, migration files, server modules, endpoint code, and UI integration changes.

---

## 3. Contract Freeze Summary

### 3.1 Frozen Decisions (D1–D11)

| ID | Decision | Locked At |
|----|----------|-----------|
| D1 | PostgreSQL canonical database | Gate 1 |
| D2 | Dual-mode auth (Google OAuth + scoped API keys) | Gate 2 |
| D3 | Single DB with workspace_id FK scoping | Gate 2 |
| D4 | ULID primaries + fingerprint secondaries | Gate 1 |
| D5 | 12-status patch lifecycle (10 visible + 2 hidden) | Gate 1 |
| D6 | No-self-approval server-enforced | Gate 1 |
| D7 | Append-only audit events, server-emitted | Gate 1 |
| D8 | Optimistic concurrency (version + 409 STALE_VERSION) | Gate 1 |
| D9 | Cursor-based pagination (50 default, 200 max) | Gate 2 |
| D10 | Soft-delete semantics (deleted_at timestamp) | Gate 2 |
| D11 | Resource-based routes (plural nouns, no verbs) | Gate 1 |

### 3.2 Frozen API Surface

| Item | Frozen Value |
|------|-------------|
| Base URL | `/api/v2.5/` |
| Resource count | 14 primary + 1 join table |
| ID format | `{prefix}_{ulid}` with 14 prefixes: `ws_`, `bat_`, `acc_`, `ctr_`, `doc_`, `pat_`, `evp_`, `sig_`, `tri_`, `aud_`, `rfi_`, `ann_`, `sel_`, `usr_` |
| Response envelope (success) | `{ data, meta: { request_id, timestamp } }` |
| Response envelope (collection) | `{ data: [], meta: { request_id, timestamp, pagination: { cursor, has_more, limit } } }` |
| Response envelope (error) | `{ error: { code, message, details }, meta: { request_id, timestamp } }` |
| Error codes (11) | `INVALID_REQUEST`, `UNAUTHORIZED`, `FORBIDDEN`, `SELF_APPROVAL_BLOCKED`, `NOT_FOUND`, `STALE_VERSION`, `DUPLICATE_RESOURCE`, `INVALID_TRANSITION`, `VALIDATION_ERROR`, `RATE_LIMITED`, `INTERNAL_ERROR` |

### 3.3 Frozen Patch Lifecycle (12 statuses)

- **Visible (10):** Draft, Submitted, Needs_Clarification, Verifier_Responded, Verifier_Approved, Admin_Approved, Admin_Hold, Applied, Rejected, Cancelled
- **Hidden (2):** Sent_to_Kiwi, Kiwi_Returned
- Full transition matrix with role requirements: frozen per canonical spec Section 7

### 3.4 Frozen Schema

- **18 tables:** `workspaces`, `batches`, `accounts`, `contracts`, `documents`, `patches`, `evidence_packs`, `annotations`, `annotation_links`, `rfis`, `triage_items`, `signals`, `selection_captures`, `audit_events`, `users`, `user_workspace_roles`, `api_keys`, `idempotency_keys`
- **25 audit event types** per canonical spec Section 10
- All field names, types, constraints from canonical spec Section 6

### 3.5 Frozen Auth Policy

| Endpoint Category | Auth Requirement |
|-------------------|-----------------|
| Human-governed (transitions, approvals) | Bearer JWT (Google OAuth) |
| Service ingestion (signals, triage) | Scoped API key (`X-API-Key`) |
| Read endpoints | Either token type |
| Health/system | No auth |

### 3.6 What Is NOT Frozen (Engineering Discretion)

| Area | Flexibility |
|------|------------|
| Python library choices | asyncpg vs psycopg2, pool library |
| FastAPI middleware patterns | Dependency injection, ordering |
| Internal file structure | Module organization within `server/` |
| Test implementation | Framework, fixture strategy |
| SSE delivery mechanism | LISTEN/NOTIFY vs polling |
| UI integration approach | Fetch wrapper, retry, cache invalidation |
| New optional schema fields | Additive without CR |
| New audit event types | Additive without CR |
| Performance optimizations | Indexes, query tuning, caching |
| Error message wording | Codes frozen, messages flexible |

### 3.7 Change Request Process

1. Create `docs/changes/CR_{NNN}_{title}.md`
2. State: which frozen item, proposed change, justification
3. Impact analysis: affected docs, code, tests
4. Approval: sign-off at the gate level where item was frozen or higher
5. If approved: update locked decision/spec, add changelog entry with date and CR reference

---

## 4. Test / Verification Plan

### 4.1 Per-Task Verification (Gate 4)

Every task has explicit acceptance criteria (see Section 1 table). Each task is verified against its criteria before marking complete.

### 4.2 Integration Verification (Gate 4 exit)

| Check | Method | Pass Criteria |
|-------|--------|---------------|
| Health endpoint | `curl /api/v2.5/health` | `{"status":"ok","db":"connected","version":"2.5.0"}` HTTP 200 |
| All 18 tables exist | `SELECT table_name FROM information_schema.tables` | All 18 present |
| Workspace CRUD round-trip | Create → Read → Update → List | Correct envelopes, version incremented |
| Batch CRUD nested | Create under workspace → Read → List | workspace_id scoped |
| Patch full lifecycle | Draft → Submitted → Verifier_Approved → Admin_Approved → Applied | All transitions succeed with correct role |
| Self-approval block | Patch author attempts own approval | HTTP 403 `SELF_APPROVAL_BLOCKED` |
| Optimistic concurrency | PATCH with stale version | HTTP 409 `STALE_VERSION` with `{current_version, provided_version}` |
| Audit trail | Mutate a resource, query audit events | Matching event with correct type, actor, before/after |
| Cursor pagination | List with limit=2 on 4+ items | `has_more: true`, valid cursor, next page correct |
| Error envelope format | Send invalid request | `{ error: { code, message, details }, meta: { request_id, timestamp } }` |
| Idempotency | POST with same key twice | Second call returns original response, not duplicate |
| Soft-delete | Delete resource, default list, list with `?include_deleted=true` | Excluded by default, visible with flag |
| RBAC enforcement | Analyst attempts admin action | HTTP 403 `FORBIDDEN` |
| API key auth | Ingest signal with scoped key | HTTP 201, workspace_id matches key scope |

### 4.3 Compliance Audit (V25-200, Gate 5)

Formal Pass/Fail report against each of the 9 non-negotiables:

1. Resource-based routes (no verb endpoints)
2. PATCH for all transitions
3. ULID primary IDs with correct prefixes
4. Optimistic concurrency (409 STALE_VERSION)
5. No-self-approval server-enforced (403 SELF_APPROVAL_BLOCKED)
6. Append-only audit_events (no UPDATE/DELETE)
7. Postgres canonical (all state in DB, not localStorage)
8. Workspace isolation (workspace_id scoping on all queries)
9. Dual-mode auth (Bearer + API key)

### 4.4 Automated Smoke Tests (V25-201, Gate 5)

Script: `scripts/v25_smoke.sh` (or Python equivalent)

Covers all 14 integration checks from Section 4.2 in an automated, idempotent, re-runnable format. Must pass on a fresh database with seed fixtures.

---

## 5. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|------------|
| R1 | Replit Postgres provisioning fails or has limits | Low | High | V25-100 is first task; fail-fast before any dependent work; Replit built-in tooling is well-tested |
| R2 | Migration conflicts on concurrent development | Low | Medium | Single developer per phase; numbered migration files with strict ordering; `schema_migrations` tracking prevents re-apply |
| R3 | ULID generation collisions | Very Low | Medium | Standard library randomness with 80 bits of entropy per ULID; collision probability negligible at our scale |
| R4 | Optimistic concurrency causes user-facing friction | Medium | Low | Clear 409 error messages with `current_version` in response; UI can auto-retry with fresh version |
| R5 | SSE connection limits under load | Low | Medium | LISTEN/NOTIFY or polling fallback; graceful disconnect handling; SSE is P1 not P0 — system functions without it |
| R6 | Transition matrix edge cases in patch lifecycle | Medium | High | Full matrix defined in canonical spec; comprehensive smoke tests cover the full Draft→Applied path + blocked transitions; hidden statuses tested separately |
| R7 | ES5 compliance regression in UI integration | Low | Medium | No arrow functions, const, let, template literals; all FE tasks (V25-140/141/142) have explicit ES5 criteria; existing 55-module extraction enforces this |
| R8 | Audit event emission performance overhead | Low | Medium | Insert within same transaction (no extra round-trip); append-only with no indexes beyond PK + workspace_id; can batch-insert if needed (flexible) |
| R9 | Auth complexity delays (Google OAuth + API keys) | Medium | Medium | Sandbox mode remains permissionless; auth is middleware-only — endpoints work identically regardless of auth source; API key path is simpler and can ship first |
| R10 | Scope creep during implementation | Medium | High | Contract Lock (Section 3) with formal Change Request process; all 11 decisions frozen; task plan frozen with explicit acceptance criteria |

---

## 6. GO Request

All Gate 3 deliverables are complete:

- [x] Final Task Plan: 30 tasks with frozen IDs, priorities, owners, dependencies, and acceptance criteria
- [x] Sequencing Lock: Phased execution order with explicit no-code-before-Gate-3 statement
- [x] Contract Freeze: 11 frozen decisions, frozen API surface, frozen schema, frozen auth policy, change request process
- [x] Test/Verification Plan: Per-task criteria, integration checks, compliance audit, automated smoke tests
- [x] Risk Register: 10 identified risks with likelihood, impact, and mitigations

**Supporting documents (unchanged, previously approved):**
- `docs/api/API_SPEC_V2_5_CANONICAL.md` — Canonical API specification
- `docs/api/openapi.yaml` — Machine-readable OpenAPI 3.1
- `docs/api/asyncapi.yaml` — SSE event definitions
- `docs/handoff/V25_LOCKED_DECISIONS.md` — 11 frozen decisions (D1–D11)
- `docs/handoff/V25_FINAL_TASK_PLAN.md` — Detailed task plan with full acceptance criteria
- `docs/handoff/V25_CONTRACT_LOCK.md` — Contract freeze details
- `docs/handoff/V25_CLARITY_MATRIX.md` — Gate 2 resolution matrix

---

**Requesting GO for Gate 4 implementation.**

All frozen decisions, task sequencing, acceptance criteria, and risk mitigations are defined. Awaiting your final GO/NO-GO.
