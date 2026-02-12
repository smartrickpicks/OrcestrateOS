# V2.5 Contract Lock Summary

**Version:** 1.0
**Date:** 2026-02-12
**Status:** Locked at Gate 3 — Change requires formal Change Request

---

## Purpose

This document defines what is now frozen for v2.5 implementation. Everything listed below was established across Gates 1-3 and cannot be modified without a formal Change Request per the process defined in `docs/handoff/V25_LOCKED_DECISIONS.md`.

---

## 1. Frozen Decisions (D1-D11)

All 11 decisions from the Locked Decisions registry are frozen. Summary:

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

Full canonical text: `docs/handoff/V25_LOCKED_DECISIONS.md`

---

## 2. Frozen API Surface

### 2.1 Base URL

`/api/v2.5/` — cannot change without CR.

### 2.2 Resource Count

14 primary resources + 1 join table. No resources may be added or removed without CR.

| Resource | ID Prefix | Parent |
|----------|-----------|--------|
| Workspace | `ws_` | — |
| Batch | `bat_` | Workspace |
| Account | `acc_` | Batch |
| Contract | `ctr_` | Batch |
| Document | `doc_` | Contract |
| Patch | `pat_` | Workspace |
| Evidence Pack | `evp_` | Patch |
| Annotation | `ann_` | Workspace |
| Annotation Link | — | Annotation |
| RFI | `rfi_` | Workspace |
| Triage Item | `tri_` | Batch |
| Signal | `sig_` | Batch |
| Selection Capture | `sel_` | Document |
| Audit Event | `aud_` | Workspace |
| User | `usr_` | — (auth-managed, not CRUD-exposed) |

### 2.3 Endpoint Routes

All endpoint paths from canonical spec Section 8 are frozen. No routes may be added, removed, or renamed without CR. The complete route listing is in `docs/api/API_SPEC_V2_5_CANONICAL.md` Section 8 and `docs/api/openapi.yaml`.

### 2.4 Response Envelopes

The three envelope formats (success, collection, error) from canonical spec Section 4 are frozen:
- Success: `{ data, meta: { request_id, timestamp } }`
- Collection: `{ data: [], meta: { request_id, timestamp, pagination: { cursor, has_more, limit } } }`
- Error: `{ error: { code, message, details }, meta: { request_id, timestamp } }`

### 2.5 Error Codes

The 11 standard error codes from canonical spec Section 4 are frozen:
`INVALID_REQUEST`, `UNAUTHORIZED`, `FORBIDDEN`, `SELF_APPROVAL_BLOCKED`, `NOT_FOUND`, `STALE_VERSION`, `DUPLICATE_RESOURCE`, `INVALID_TRANSITION`, `VALIDATION_ERROR`, `RATE_LIMITED`, `INTERNAL_ERROR`

---

## 3. Frozen Schema

### 3.1 Resource Schemas

All field names, types, and constraints from canonical spec Section 6 are frozen. Adding new optional fields is permitted without CR. Removing fields, changing types, or renaming fields requires CR.

### 3.2 Database Tables

The 18 tables defined in task V25-102 are frozen:
`workspaces`, `batches`, `accounts`, `contracts`, `documents`, `patches`, `evidence_packs`, `annotations`, `annotation_links`, `rfis`, `triage_items`, `signals`, `selection_captures`, `audit_events`, `users`, `user_workspace_roles`, `api_keys`, `idempotency_keys`

Adding new indexes or constraints is permitted. Removing columns or tables requires CR.

### 3.3 ID Format

`{prefix}_{ulid}` format with 14 defined prefixes. Prefixes and format cannot change without CR.

---

## 4. Frozen Auth Policy

| Category | Auth Requirement | Frozen |
|----------|-----------------|--------|
| Human-governed endpoints | Bearer JWT (from Google OAuth) | Yes |
| Service ingestion endpoints | Scoped API key (`X-API-Key`) | Yes |
| Read endpoints | Either token type | Yes |
| Health/system endpoints | No auth | Yes |
| OAuth flow | Google OIDC → server JWT (1h) | Yes |
| API key model | Workspace-scoped, hashed, revocable | Yes |

---

## 5. Frozen Patch Lifecycle

The 12-status lifecycle (10 visible + 2 hidden) and full transition matrix from canonical spec Section 7 are frozen. The 10 visible statuses are: Draft, Submitted, Needs_Clarification, Verifier_Responded, Verifier_Approved, Admin_Approved, Admin_Hold, Applied, Rejected, Cancelled. The 2 hidden statuses are: Sent_to_Kiwi, Kiwi_Returned. No statuses may be added, removed, or renamed. No transitions may be added or removed. Role requirements on each transition are fixed.

---

## 6. Frozen Audit Event Types

The 25 event types from canonical spec Section 10 are frozen. New event types may be added without CR (additive change). Existing event types cannot be removed or renamed without CR.

---

## 7. Frozen Task Plan

The task IDs, dependencies, and acceptance criteria in `docs/handoff/V25_FINAL_TASK_PLAN.md` are frozen. Task reordering within the same phase is permitted if dependencies are respected. Adding net-new tasks requires CR.

---

## 8. What Is NOT Frozen

The following implementation details are explicitly left to engineering discretion:

| Area | Flexibility |
|------|------------|
| Python library choices | asyncpg vs psycopg2, connection pool library |
| FastAPI middleware patterns | Dependency injection, middleware ordering |
| Internal file structure | Module organization within `server/` |
| Test implementation | Test framework, fixture strategy |
| SSE delivery mechanism | LISTEN/NOTIFY vs polling |
| UI integration approach | Fetch wrapper, retry strategy, cache invalidation |
| New optional schema fields | May be added without CR |
| New audit event types | May be added without CR |
| Performance optimizations | Indexes, query optimization, caching |
| Error message wording | Exact message strings (codes are frozen, messages are not) |

---

## 9. Change Request Process

To modify anything listed as frozen:

1. Create `docs/changes/CR_{NNN}_{title}.md`
2. State: which frozen item, proposed change, justification
3. Impact analysis: affected docs, code, tests
4. Approval: requires sign-off at the gate level where the item was frozen or higher
5. If approved: update the locked decision/spec, add changelog entry with date and CR reference

---

## Cross-References

- `docs/handoff/V25_LOCKED_DECISIONS.md` — 11 frozen decisions with canonical text
- `docs/handoff/V25_FINAL_TASK_PLAN.md` — Frozen task plan with acceptance criteria
- `docs/api/API_SPEC_V2_5_CANONICAL.md` — Canonical API specification
- `docs/api/openapi.yaml` — Machine-readable endpoint spec
- `docs/handoff/V25_CLARITY_MATRIX.md` — Gate 2 resolution details
