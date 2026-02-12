# V2.5 Task List

**Version:** 0.3 (Gate 3 Complete)
**Date:** 2026-02-12
**Status:** Gate 3 Complete — Ready for Gate 4 (Code)

---

## Task Dependency Graph

```
Gate 1 (Docs)
  V25-001 Readiness Report ──┐
  V25-002 DB Decision Lock ──┤
  V25-003 Canonical Spec ────┤──→ Gate 2 (Clarity)
  V25-004 OpenAPI Spec ──────┤      V25-020 Clarity Matrix
  V25-005 AsyncAPI Spec ─────┤      V25-021 Locked Decisions
  V25-006 Task List ─────────┘
                                 ──→ Gate 3 (Alignment Baseline)
                                        V25-030 Final Task Plan
                                        V25-031 Contract Lock
                                 ──→ Gate 4 (Code)
                                        V25-100 DB Provisioning
                                        V25-101 Migration Framework
                                        V25-102 Core Tables Migration
                                        V25-103 Seed Fixtures
                                        V25-104 DB Connection Layer
                                        V25-105 ULID ID Generator
                                        V25-106 Health Endpoint
                                        V25-110 Workspace CRUD
                                        V25-111 Batch CRUD
                                        V25-112 Contract/Document CRUD
                                        V25-113 Account CRUD
                                        V25-114 Patch CRUD + Transitions
                                        V25-115 Evidence Pack CRUD
                                        V25-116 Annotation CRUD
                                        V25-117 RFI CRUD
                                        V25-118 Triage Item CRUD
                                        V25-119 Signal CRUD
                                        V25-120 Selection Capture CRUD
                                        V25-121 Audit Event Read API
                                        V25-130 RBAC Middleware
                                        V25-131 Self-Approval Gate
                                        V25-132 Optimistic Concurrency
                                        V25-133 Idempotency Keys
                                        V25-134 Audit Event Emission
                                        V25-135 SSE Event Stream
                                        V25-140 UI Workspace Mode Wire
                                        V25-141 UI Audit Data Flow
                                        V25-142 Selection Capture Path
                                 ──→ Gate 5 (Audit)
                                        V25-200 Compliance Audit
                                        V25-201 Smoke Tests
```

---

## Gate 1 Tasks (DOCS — Current)

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-001 | P0 | Docs | None | **Done** | Readiness report at `docs/handoff/V25_READINESS_REPORT.md` with Done/Partial/Missing matrix, file paths, line refs, risk levels |
| V25-002 | P0 | Docs | None | **Done** | DB decision record at `docs/decisions/DECISION_V25_DB.md` with PostgreSQL lock, rationale, migration strategy |
| V25-003 | P0 | Docs | V25-001 | **Done** | Canonical spec at `docs/api/API_SPEC_V2_5_CANONICAL.md` with 14 resource schemas, transition matrix, RBAC, envelopes, concurrency semantics |
| V25-004 | P0 | Docs | V25-003 | **Done** | OpenAPI 3.1 at `docs/api/openapi.yaml` covering all /api/v2.5/ endpoints |
| V25-005 | P1 | Docs | V25-003 | **Done** | AsyncAPI at `docs/api/asyncapi.yaml` with SSE event envelope and topic definitions |
| V25-006 | P0 | Docs | V25-001 | **Done** | This task list at `docs/handoff/V25_TASK_LIST.md` |
| V25-007 | P1 | Docs | V25-006 | **Done** | Update `docs/INDEX.md` with links to all new v2.5 docs |

---

## Gate 2 Tasks (CLARITY — Complete)

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-020 | P0 | Docs | Gate 1 approved | **Done** | Clarity Matrix at `docs/handoff/V25_CLARITY_MATRIX.md` — all blocking questions resolved, contradictions documented |
| V25-021 | P0 | Docs | V25-020 | **Done** | Locked Decisions at `docs/handoff/V25_LOCKED_DECISIONS.md` — 11 decisions frozen with canonical text |
| V25-022 | P0 | Docs | V25-020 | **Done** | Canonical API spec updated with Gate 2 auth policy (dual-mode, endpoint classification, API key model, OAuth flow) |
| V25-023 | P0 | Docs | V25-022 | **Done** | OpenAPI spec security schemes updated (BearerToken, ScopedApiKey, GoogleOAuth) |

---

## Gate 3 Tasks (ALIGNMENT — Complete)

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-030 | P0 | Docs | Gate 2 approved | **Done** | Final Task Plan at `docs/handoff/V25_FINAL_TASK_PLAN.md` — frozen acceptance criteria, sequencing, dependencies for 30 tasks across 4 phases |
| V25-031 | P0 | Docs | V25-030 | **Done** | Contract Lock Summary at `docs/handoff/V25_CONTRACT_LOCK.md` — frozen items, flexibility areas, CR process |

---

## Gate 4 Tasks (CODE — Pending Gate 3 Approval)

### Phase 2: Persistence Foundation

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-100 | P0 | BE | Gate 3 approved | Pending | PostgreSQL provisioned via Replit, DATABASE_URL available |
| V25-101 | P0 | BE | V25-100 | Pending | `server/migrations/` directory with Python migration runner; runner executes on server startup |
| V25-102 | P0 | BE | V25-101 | Pending | Migration `001_core_tables.sql` with all 17+ tables, indexes, constraints, append-only policy on audit_events |
| V25-103 | P1 | BE | V25-102 | Pending | Migration `002_seed_fixtures.sql` with deterministic dev data (workspace, users, roles, batch, accounts, contracts) |
| V25-104 | P0 | BE | V25-100 | Pending | Database connection layer (asyncpg or psycopg2), connection pooling, graceful shutdown |
| V25-105 | P0 | BE | None | Pending | ULID-like ID generator with all 14 prefixes (bat_, acc_, ctr_, doc_, pat_, evp_, sig_, tri_, aud_, ws_, rfi_, ann_, sel_, usr_) |
| V25-106 | P0 | BE | V25-104 | Pending | `/api/v2.5/health` endpoint returning `{ status, db, version }` |

### Phase 3: API Implementation

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-110 | P0 | BE | V25-106 | Pending | Workspace CRUD (GET list, POST, GET by ID, PATCH) with response envelope |
| V25-111 | P0 | BE | V25-110 | Pending | Batch CRUD nested under workspace |
| V25-112 | P1 | BE | V25-111 | Pending | Contract + Document CRUD nested under batch/contract |
| V25-113 | P1 | BE | V25-111 | Pending | Account CRUD nested under batch |
| V25-114 | P0 | BE | V25-111 | Pending | Patch CRUD with full transition matrix enforcement, history tracking |
| V25-115 | P1 | BE | V25-114 | Pending | Evidence Pack CRUD nested under patch |
| V25-116 | P1 | BE | V25-110 | Pending | Annotation + Annotation Link CRUD |
| V25-117 | P1 | BE | V25-114 | Pending | RFI CRUD with status transitions |
| V25-118 | P1 | BE | V25-111 | Pending | Triage Item CRUD nested under batch |
| V25-119 | P2 | BE | V25-111 | Pending | Signal CRUD (create + read only) |
| V25-120 | P2 | BE | V25-112 | Pending | Selection Capture CRUD nested under document |
| V25-121 | P1 | BE | V25-110 | Pending | Audit Event read API (GET list, GET by ID, filterable) |
| V25-130 | P0 | BE | V25-110 | Pending | RBAC middleware — role resolution from user_workspace_roles, permission checks on all mutating endpoints |
| V25-131 | P0 | BE | V25-114, V25-130 | Pending | Self-approval gate — 403 SELF_APPROVAL_BLOCKED on Verifier_Approved/Admin_Approved when actor === author |
| V25-132 | P0 | BE | V25-110 | Pending | Optimistic concurrency — version field on all PATCH, 409 STALE_VERSION on mismatch |
| V25-133 | P1 | BE | V25-110 | Pending | Idempotency key support — Idempotency-Key header on POST, 24h expiry, 409 on duplicate with different payload |
| V25-134 | P0 | BE | V25-106 | Pending | Audit event emission — server-side append-only insert on every mutating API call |
| V25-135 | P1 | BE | V25-134 | Pending | SSE event stream at `/workspaces/{ws_id}/events/stream` with Last-Event-ID resumption |

### Phase 4: UI Integration

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-140 | P1 | FE | V25-110 | Pending | Workspace mode persisted via API; UI reads from server on load |
| V25-141 | P1 | FE | V25-121, V25-135 | Pending | Audit timeline data sourced from API + SSE stream |
| V25-142 | P2 | FE | V25-120 | Pending | SelectionCapture persistence path — field_id to selection_id trace linkage |

---

## Gate 5 Tasks (AUDIT — Post-Code)

| ID | Priority | Owner | Dependencies | Status | Acceptance Criteria |
|----|----------|-------|-------------|--------|-------------------|
| V25-200 | P0 | Fullstack | Gate 4 complete | Pending | Compliance audit report: Pass/Fail for each non-negotiable (endpoint naming, concurrency, RBAC, self-approval, audit append-only, Postgres canonical) |
| V25-201 | P0 | Fullstack | V25-200 | Pending | Smoke test suite: OpenAPI served, key v2.5 endpoints valid, patch transitions enforced, self-approval blocked, audit append-only, fixtures deterministic |

---

## Open Questions — All Resolved (Gate 2)

All questions resolved. See `docs/handoff/V25_LOCKED_DECISIONS.md` for canonical text.

| # | Question | Resolution |
|---|----------|-----------|
| Q1 | Authentication | **Locked (D2):** Google OAuth (OIDC) for human users, scoped API keys for service ingestion |
| Q2 | Workspace isolation | **Locked (D3):** Single DB with workspace_id FK scoping |
| Q3 | Pagination | **Locked (D9):** Cursor-based, 50 default, 200 max |
| Q4 | Rate limiting | **Deferred:** Not in v2.5 scope |
| Q5 | Blob storage | **Accepted:** URL references only, no blob store |
| Q6 | Delete semantics | **Locked (D10):** Soft-delete (deleted_at timestamp) |
