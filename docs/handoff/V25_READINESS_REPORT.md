# V2.5 Readiness Report

**Version:** 0.1 (Gate 1 Draft)
**Date:** 2026-02-12
**Status:** Pending Alignment Approval

---

## 1. Executive Summary

Orchestrate OS is a mature frontend-only governance UI (19,241-line monolith in `ui/viewer/index.html`) with well-defined roles, gates, audit events, and a 12-status patch lifecycle (10 visible + 2 hidden) — all running entirely in the browser (localStorage + IndexedDB). API v2.5 introduces Postgres-backed multi-user persistence, server-side audit emission, and canonical resource-style endpoints.

This report audits the current repo against v2.5 requirements and identifies what exists, what conflicts, and what is missing.

---

## 2. Readiness Matrix

| # | Area | Status | Risk | Evidence |
|---|------|--------|------|----------|
| R1 | Role definitions (Analyst/Verifier/Admin) | **Done** | Low | `docs/ui/roles/analyst.md`, `docs/ui/roles/verifier.md`, `docs/ui/roles/admin.md` — clear can/cannot matrices, allowed transitions |
| R2 | Gate decisions (G1-G8+) | **Done** | Low | `docs/memos/V23_GATE_DECISIONS.md` — locked, deterministic console logs per gate |
| R3 | Patch lifecycle (11-status) | **Partial** | Medium | `ui/viewer/index.html:11783-11796` — `PATCH_REQUEST_STATUSES` array defines: Draft, Submitted, Needs_Clarification, Verifier_Responded, Verifier_Approved, Admin_Approved, Applied, Rejected, Cancelled, Admin_Hold (+ hidden: Sent_to_Kiwi, Kiwi_Returned). Transition logic at line 12088. **Gap:** browser-only state in localStorage via `PATCH_REQUEST_STORE` (line 6067) |
| R4 | Audit event schema | **Partial** | Medium | `docs/AUDIT_LOG.md` — 20+ event types, schema (evt_ prefix, actor_role, timestamp_iso). Implementation at `ui/viewer/index.html:12129` via `AuditTimeline.emit()`. Storage in IndexedDB `orchestrate_audit`. **Gap:** client-generated, not server-emitted |
| R5 | No-self-approval rule | **Partial** | High | `ui/viewer/index.html:31680-31684` — `isSelfApproval()` compares `currentUser` vs `patchRequest.author`. Enforced at lines 12983, 37788, 38094. **Gap:** UI-enforced only, no server-side gate |
| R6 | ID model | **Conflict** | High | `docs/memos/V23_ID_MODEL.md` — V2.3 uses hash-based IDs (`ctr_{hash}`, `doc_{hash}`, `batch_{timestamp}_{random}`). V2.5 requires ULID-like primary IDs with fingerprints as secondary fields. See Conflict C1 below |
| R7 | Evidence packs | **Partial** | Medium | `docs/ui_evidence_pack.md` — 4-block structure defined. Browser-side construction only. **Gap:** no server persistence, no `evidence_pack` resource |
| R8 | Artifact store | **Partial** | High | `docs/INTERFACES.md` — `fs:` mock filesystem in localStorage. Artifact IDs: `art_{dataset}_{record}_{field}_{timestamp}`. **Gap:** localStorage-backed, needs migration to Postgres |
| R9 | Storage policy | **Done** | Low | `docs/decisions/DECISION_STORAGE_POLICY.md` — localStorage for prefs/pointers, IndexedDB for payloads. V2.3 locked |
| R10 | Contract hierarchy | **Done** | Low | `docs/decisions/DECISION_HIERARCHY.md` — batch→contract→document→sheet→row. Rebuild-from-live policy locked |
| R11 | Mode/role switching | **Partial** | Medium | `ui/viewer/index.html:5443` — `currentMode` variable. `localStorage.getItem('viewer_mode_v10')` at line 6570. **Gap:** no server-persisted user mode or workspace preferences |
| R12 | BroadcastChannel | **N/A** | Low | Not found in codebase. V2.5 non-negotiable preserved by default |
| R13 | SelectionCapture | **Missing** | Medium | No `SelectionCapture`, `selection_capture`, or `selectionCapture` found in codebase |
| R14 | API endpoints (/api/v2.5/) | **Missing** | Critical | No API routes exist. Only `server/pdf_proxy.py` (PDF proxy) |
| R15 | OpenAPI / AsyncAPI specs | **Missing** | Critical | No files in `docs/api/` |
| R16 | PostgreSQL persistence | **Missing** | Critical | No database provisioned. No SQL files. No migrations |
| R17 | Server-side RBAC middleware | **Missing** | Critical | Roles defined in docs but no auth/middleware implementation |
| R18 | SSE event stream | **Missing** | High | No server-sent events implementation |
| R19 | Idempotency / concurrency | **Missing** | High | No optimistic concurrency (409 STALE_VERSION), no idempotency keys |
| R20 | RFI / Annotation resources | **Partial** | Medium | `docs/rfi/document_layer_v1.md` defines RFI concepts. No API resource definition |

---

## 3. Conflicts Requiring Resolution

### C1: ID Model (V2.3 → V2.5)

**Current (V2.3):**
- `batch_id`: `batch_{timestamp}_{random}` — session-scoped, regenerated on rebuild
- `contract_id`: `ctr_{hash(fileId|canonUrl|fileName)}` — deterministic hash-based
- `document_id`: `doc_{hash(combined)}` — deterministic hash-based
- `record_id`: `hash(tenant+dataset+canonicalizedRow)` or `row_{idx}` fallback
- Source: `docs/memos/V23_ID_MODEL.md`, `ui/viewer/index.html` ContractIndex engine

**Required (V2.5):**
- Primary IDs: prefixed ULID-like IDs (bat_, acc_, ctr_, doc_, pat_, evp_, sig_, tri_, aud_, ws_, rfi_, ann_, sel_)
- Deterministic fingerprints: secondary fields only (not primary keys)

**Proposed Resolution:**
- Introduce ULID-like primary keys as canonical identifiers for all server-side resources
- Preserve existing hash-based IDs as `_fingerprint` columns (e.g., `contract_fingerprint`, `document_fingerprint`, `record_fingerprint`)
- Fingerprint columns are indexed for deduplication and cross-reference
- UI can continue displaying/using fingerprints; API requests/responses use ULID IDs
- Mapping: on first server-side ingest, each entity gets a ULID primary key; the existing hash-based ID is stored as the fingerprint
- Both coexist permanently; fingerprints are immutable once set

### C2: Artifact Store Migration (localStorage → Postgres)

**Current:**
- `fs:.orchestrate/workspaces/{ws}/artifacts/{id}` in localStorage
- `PATCH_REQUEST_STORE` using `pr:` prefix keys in localStorage (line 6067-6097)
- Artifact IDs: `art_{dataset}_{record}_{field}_{timestamp}`
- Thread IDs: `thr_{artifact_id}`

**Required (V2.5):**
- All durable collaboration/governance state in Postgres

**Proposed Resolution:**
- Postgres becomes canonical store for all artifacts, patches, threads
- Browser localStorage/IndexedDB becomes a read-cache for offline-first UX
- API writes are authoritative; client reads can use cache with staleness awareness
- Legacy `fs:` and `pr:` paths become client-side cache layer, not source of truth
- Migration path: API provides bulk import endpoint; client can push existing localStorage data to server on first connect

### C3: Audit Events (Client-side → Server-side)

**Current:**
- `AuditTimeline.emit()` at `ui/viewer/index.html:12129` generates events client-side
- Stored in IndexedDB `orchestrate_audit` database
- Schema: `evt_{timestamp_base36}_{random}`, 20+ event types
- Used for in-app timeline display and XLSX export

**Required (V2.5):**
- Audit events are append-only and server-side generated on all writes

**Proposed Resolution:**
- Server generates canonical audit events on every mutating API call
- Existing event schema maps directly to server `audit_events` table (same fields)
- Client receives events via SSE stream for real-time timeline updates
- IndexedDB becomes a local mirror for offline display and export
- Dual-write period: during transition, client can continue emitting locally while server adoption rolls out
- Event IDs: server uses ULID-like `aud_` prefix; client-generated `evt_` IDs become legacy

---

## 4. PATCH_REQUEST_STORE Analysis

**Location:** `ui/viewer/index.html:6067-6097`

The current patch request store is a localStorage-backed object with get/save/list/remove methods. Key behaviors:
- Keys: `pr:{environment}:{patch_request_id}`
- Saves full patch request JSON to localStorage
- Status normalization via `normalizeLegacyStatus()` on read
- Role normalization via `normalizeLegacyRole()` on read

**Transition function:** `updatePatchRequestStatus()` at line 12088:
- Validates new status against `PATCH_REQUEST_STATUSES` array
- Calls `canTransition(from, to, role)` for RBAC-gated transitions
- Appends to `request.history[]` and `request.audit_log[]`
- Emits `AuditTimeline.emit()` with full context
- Calls `savePatchRequests()` to persist

**V2.5 mapping:** This entire flow moves server-side. The `PATCH /api/v2.5/patches/{id}` endpoint replaces `updatePatchRequestStatus()`. Transition validation, audit emission, and persistence happen atomically in Postgres.

---

## 5. Existing Patch Statuses (11 Visible + 2 Hidden)

Source: `ui/viewer/index.html:11783-11796`

| Status | Role Required | Visibility | Description |
|--------|--------------|-----------|-------------|
| Draft | Analyst | Visible | Initial authoring state |
| Submitted | Analyst | Visible | Submitted to review queue |
| Needs_Clarification | Verifier | Visible | Verifier requests more info |
| Verifier_Responded | Analyst | Visible | Analyst responds to clarification |
| Verifier_Approved | Verifier | Visible | Approved at verifier gate |
| Admin_Approved | Admin | Visible | Approved at admin gate |
| Admin_Hold | Admin | Visible | Blocked by admin pending review |
| Applied | Admin | Visible | Patch applied to target |
| Rejected | Verifier/Admin | Visible | Patch rejected |
| Cancelled | Analyst | Visible | Author-cancelled |
| Sent_to_Kiwi | Admin | Hidden (V1) | Exported for external processing |
| Kiwi_Returned | Admin | Hidden (V1) | Returned from external processing |

---

## 6. No-Self-Approval Implementation

Source: `ui/viewer/index.html:31680-31684`

```javascript
function isSelfApproval(patchRequest) {
  if (!patchRequest) return false;
  var currentUser = getCurrentUserName();
  return currentUser && patchRequest.author &&
    currentUser.toLowerCase() === patchRequest.author.toLowerCase();
}
```

Enforcement points:
- Line 12983: Verifier approval gate
- Line 37788: Admin approval view
- Line 38094: Admin promotion view

**V2.5 mapping:** Server enforces this on PATCH transitions to `Verifier_Approved` and `Admin_Approved`. Returns 403 with code `SELF_APPROVAL_BLOCKED`.

---

## 7. Open Questions — All Resolved (Gate 2)

All blocking questions resolved. See `docs/handoff/V25_CLARITY_MATRIX.md` for full details.

| # | Question | Resolution |
|---|----------|-----------|
| Q1 | Authentication mechanism | **Locked:** Google OAuth (OIDC) for human users, scoped API keys for service ingestion |
| Q2 | Multi-workspace isolation | **Locked:** Single DB with strict `workspace_id` FK scoping |
| Q3 | Pagination model | **Accepted:** Cursor-based, 50 default, 200 max |
| Q4 | Rate limiting | **Deferred:** Not in v2.5 scope |
| Q5 | File/blob storage | **Accepted:** URL references only, no blob store |
| Q6 | Delete semantics | **Accepted:** Soft-delete (`deleted_at` timestamp) |

---

## 8. Risk Register

| # | Risk | Likelihood | Impact | Mitigation |
|---|------|-----------|--------|-----------|
| RK1 | Governance regression during localStorage→Postgres migration | Medium | Critical | Dual-write transition period; feature flags per resource |
| RK2 | ID model confusion (fingerprint vs ULID) in UI code | Medium | High | Clear mapping doc; deprecation warnings in console |
| RK3 | Audit event completeness gap during transition | Medium | High | Client continues local emission until server adoption verified |
| RK4 | Self-approval bypass if server enforcement incomplete | Low | Critical | Server-side check is P0; cannot ship without it |
| RK5 | BroadcastChannel creep into backend sync | Low | Medium | Architectural constraint already absent in codebase |
