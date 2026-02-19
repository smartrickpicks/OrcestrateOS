# V2.5 Locked Decisions

**Version:** 1.0
**Date:** 2026-02-12
**Status:** Locked — Change requires formal Change Request

---

## Purpose

This document records all decisions that are now frozen for v2.5 implementation. Any modification to these decisions requires a formal Change Request with justification and impact analysis.

---

## Decision Registry

### D1: Canonical Database — PostgreSQL

**Locked at:** Gate 1
**Document:** `docs/decisions/DECISION_V25_DB.md`

PostgreSQL is the single canonical store for all durable collaboration and governance state. SQLite or other stores may only serve as optional local dev fallback and must be clearly marked non-canonical. All mutating operations go through the API; the database is not directly accessed by clients.

---

### D2: Authentication — Dual-Mode (Google OAuth + Scoped API Keys)

**Locked at:** Gate 2
**Document:** `docs/handoff/V25_CLARITY_MATRIX.md` (Auth Policy Detail)

- **Production human users:** Google OAuth (OIDC) with email-based identity resolution
- **Sandbox and service ingestion:** Scoped API keys bound to a single workspace
- **Endpoint policy:**
  - Human-governed endpoints (patch transitions, approvals, annotations): require user token (Bearer JWT)
  - Service ingestion endpoints (signals, triage items, bulk batch ingest): require scoped API key with explicit permission grants
  - Read endpoints: accept either token type
  - Health/system endpoints: no auth required
- **Session tokens:** JWT, 1-hour expiry, server-issued after OAuth code exchange
- **API key storage:** Hashed (only prefix visible after creation), workspace-scoped, revocable

---

### D3: Workspace Isolation — Single DB with workspace_id Scoping

**Locked at:** Gate 2
**Document:** `docs/handoff/V25_CLARITY_MATRIX.md` (Workspace Isolation Detail)

- Single Postgres database for all workspaces
- `workspace_id` is a mandatory foreign key on all governed resource tables
- Every query includes `workspace_id` in its WHERE clause — enforced at repository layer
- Cross-workspace queries are architecturally forbidden
- Composite indexes use `workspace_id` as leading column
- Optional RLS hardening via session variable (`app.workspace_id`)
- Schema-per-workspace is explicitly out of scope for v2.5

---

### D4: ID Model — ULID Primaries + Fingerprint Secondaries

**Locked at:** Gate 1
**Document:** `docs/handoff/V25_READINESS_REPORT.md` (Conflict C1)

- Primary IDs: Prefixed ULID-like identifiers for all server-side resources (e.g., `pat_01HXY...`, `ctr_01HXY...`)
- Fingerprints: V2.3 hash-based IDs preserved as `_fingerprint` columns (e.g., `contract_fingerprint`)
- Fingerprint columns are indexed for deduplication and cross-reference
- Both coexist permanently; fingerprints are immutable once set
- API requests/responses use ULID IDs; UI may display either

---

### D5: Patch Lifecycle — 12 Statuses (10 Visible + 2 Hidden)

**Locked at:** Gate 1 (refined Gate 2)
**Document:** `docs/api/API_SPEC_V2_5_CANONICAL.md` (Section 7)

Visible: Draft, Submitted, Needs_Clarification, Verifier_Responded, Verifier_Approved, Admin_Approved, Admin_Hold, Applied, Rejected, Cancelled

Hidden: Sent_to_Kiwi, Kiwi_Returned

Full transition matrix with role requirements and self-approval gates is defined in the canonical spec.

---

### D6: No-Self-Approval — Server-Enforced

**Locked at:** Gate 1
**Document:** `docs/api/API_SPEC_V2_5_CANONICAL.md` (Section 5, 7)

- Server rejects PATCH to `Verifier_Approved` when `actor_id === patch.author_id` → 403 `SELF_APPROVAL_BLOCKED`
- Server rejects PATCH to `Admin_Approved` when `actor_id === patch.author_id` → 403 `SELF_APPROVAL_BLOCKED`
- This is enforced server-side regardless of client behavior
- Cannot be overridden by any role including Architect

---

### D7: Audit Events — Append-Only, Server-Emitted

**Locked at:** Gate 1
**Document:** `docs/api/API_SPEC_V2_5_CANONICAL.md` (Section 6.14, 10)

- `audit_events` table: no UPDATE, no DELETE operations permitted
- All audit events are server-generated on mutating API calls
- Corrections are new events referencing prior event IDs
- 25 event types defined (see canonical spec Section 10)
- SSE delivery for real-time cross-user streaming

---

### D8: Optimistic Concurrency — Version Field + 409 STALE_VERSION

**Locked at:** Gate 1
**Document:** `docs/api/API_SPEC_V2_5_CANONICAL.md` (Section 9)

- Every mutable resource has a `version` integer field (starts at 1, increments on each write)
- All PATCH requests must include `"version": N` in the body
- If current DB version differs from provided version: 409 with code `STALE_VERSION`
- Client must re-read and re-submit with current version

---

### D9: Pagination — Cursor-Based

**Locked at:** Gate 2 (accepted default)

- Cursor-based pagination on all collection endpoints
- Default limit: 50 items
- Maximum limit: 200 items
- Cursor is opaque (base64-encoded compound key)

---

### D10: Soft-Delete Semantics

**Locked at:** Gate 2 (accepted default)

- Governed resources use soft-delete (`deleted_at` timestamp)
- Soft-deleted resources excluded from default queries
- Soft-deleted resources visible with `?include_deleted=true` query parameter
- Audit events are never soft-deleted (append-only)

---

### D11: Resource-Based Routes

**Locked at:** Gate 1
**Document:** `docs/api/API_SPEC_V2_5_CANONICAL.md` (Section 2, 8)

- All endpoints use plural noun resource names
- No verb-based endpoints
- Nested resources under parent (e.g., `/workspaces/{ws_id}/batches`)
- Direct access by ID (e.g., `/batches/{id}`)
- PATCH for all updates and status transitions

---

## Change Request Process

To modify any locked decision:

1. Open a Change Request document in `docs/changes/CR_{NNN}_{title}.md`
2. State: which decision, what change, why
3. Impact analysis: which docs, code, and tests are affected
4. Approval: requires sign-off from the same gate level or higher
5. If approved: update the locked decision, add a changelog entry with date and CR reference
