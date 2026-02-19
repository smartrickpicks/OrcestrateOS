# V2.54 Verifier Operations View — Clarity Phase

**Version:** 2.54  
**Date:** 2026-02-17  
**Status:** LOCKED — Clarity Phase  
**Scope:** Locked decisions, API/UI mismatch register, migration/cutover plan, Go/No-Go  

---

## 1. Locked Decisions Applied

### LD-01: Annotation Layer Is First-Class Artifact

**Decision:** The Annotation Layer (patches, RFIs, corrections, anchors, evidence marks, audit events) is the canonical governance truth for Verifier and Admin operations.

**Implications:**
- All verifier/admin actions write to the DB Annotation Layer
- Source documents (PDFs, XLSX sheets) are context-only, never governance truth
- If a source document is unavailable, annotation cards still render and the verifier workflow still functions
- Dashboard reads DB-cached state only; no extraction recompute at query time

### LD-02: Operations View Is Multi-Batch and DB-First

**Decision:** The Operations View is workspace-scoped, showing governance items across all batches. It reads from the DB, not from localStorage.

**Implications:**
- The composite queue endpoint (`GET /workspaces/{ws}/operations/queue`) queries across all batches
- Batch filtering is optional (query param), not the default scope
- localStorage-driven `verifierQueueState` is deprecated and will be replaced by DB-first hydration

### LD-03: "Operations View" Naming Standard

**Decision:** Use "Operations View" consistently in all code, UI labels, API documentation, and decision docs.

**Deprecated names:** ~~"All"~~, ~~"Verifier Dashboard"~~, ~~"Triage"~~ (reserved for analyst triage).

### LD-04: Data Precedence

**Decision:** Locked in `V254_ANNOTATION_LAYER_ARTIFACT_SPEC.md` §4. Summary:

1. **DB Annotation Layer** — canonical
2. **Imported workbook snapshot** — baseline context only
3. **Drive metadata/provenance** — storage metadata only
4. **localStorage** — temporary transition fallback only; never canonical

### LD-05: Additive-Only API Evolution

**Decision:** All API changes are additive (new query params, new endpoints). No endpoint removals, renames, or breaking response shape changes. Existing clients continue working unchanged.

### LD-06: RBAC + Workspace Isolation on Every Path

**Decision:** Every read and write path validates:
1. User has a role in the target workspace
2. User's role meets the minimum required for the operation
3. Self-approval is blocked at the server level

### LD-07: Verifier Actions Write to DB Only

**Decision:** When implemented, `vrApprove()`, `vrReject()`, RFI custody transitions, and correction approvals will call server endpoints. They will NOT write to localStorage as the primary store.

**Transition:** During migration, a dual-write is acceptable (write to server, update localStorage as cache). After migration, localStorage writes are removed entirely.

---

## 2. API/UI Mismatch Register

### 2.1 Critical Mismatches (Block Verifier DB-First)

| ID | Mismatch | UI Location | API Location | Severity |
|----|----------|-------------|-------------|----------|
| M-01 | **Verifier queue loads from localStorage, not DB** | `index.html` L39092: `verifierQueueState.payloads = JSON.parse(localStorage.getItem('srr_verifier_queue_v1'))` | `GET /workspaces/{ws}/patches` exists but is never called by verifier queue | **CRITICAL** |
| M-02 | **vrApprove writes to localStorage, not DB** | `index.html` L44331–44356: `vrApprove()` sets `vrState.reviewState = 'Verifier_Approved'`, calls `vrLogAuditEvent()` which writes to `ARTIFACT_STORE.fsAppend('events.jsonl')` (localStorage) | `PATCH /patches/{id}` with status transition matrix exists (patches.py L26–48) but is never called | **CRITICAL** |
| M-03 | **vrReject writes to localStorage, not DB** | `index.html` L44359–44375: `vrReject()` sets `vrState.reviewState = 'Rejected'`, writes to localStorage audit | `PATCH /patches/{id}` exists but is never called | **CRITICAL** |
| M-04 | **updatePayloadStatus writes to localStorage, not DB** | `index.html` L43207–43260: Updates `verifierQueueState.payloads[].status`, calls `saveVerifierQueue()` → `localStorage.setItem(...)` | No corresponding API call | **CRITICAL** |
| M-05 | **RFI custody transitions are localStorage-only** | `index.html` L43207+: Status changes go through `updatePayloadStatus()` which writes to localStorage | `PATCH /rfis/{id}` with custody transition matrix exists (rfis.py L20–26) but is never called from verifier UI | **CRITICAL** |

### 2.2 Batch-Scoping Mismatches

| ID | Mismatch | File | Line | Expected | Actual |
|----|----------|------|------|----------|--------|
| M-06 | **`list_batch_rfis` is workspace-scoped, not batch-scoped** | `server/routes/rfis.py` | L500–501 | Returns RFIs belonging to records in the target batch | Returns ALL workspace RFIs where `workspace_id` matches the batch's workspace |
| M-07 | **`batch_health` RFI counts are workspace-wide** | `server/routes/batch_health.py` | L40–51 | Counts RFIs scoped to the target batch | Counts ALL workspace RFIs |
| M-08 | **No `record_id` filter on patches list** | `server/routes/patches.py` | L89–149 | `GET /workspaces/{ws}/patches?record_id=X` filters by record | `record_id` query param not implemented; must fetch all and filter client-side |
| M-09 | **No `batch_id` filter on RFI list** | `server/routes/rfis.py` | L76–130 | `GET /workspaces/{ws}/rfis?batch_id=X` filters by batch | `batch_id` query param not implemented |
| M-10 | **No `target_type`/`target_id` filter on annotations** | `server/routes/annotations.py` | L36+ | `GET /workspaces/{ws}/annotations?target_type=patch&target_id=X` | No filter params; returns all workspace annotations |

### 2.3 Missing Endpoints

| ID | Missing Endpoint | Description |
|----|-----------------|-------------|
| M-11 | `GET /workspaces/{ws}/corrections` | No workspace-level correction list. Corrections can only be listed by document or by batch. |
| M-12 | `GET /workspaces/{ws}/operations/queue` | No composite queue endpoint. Verifier must query patches, RFIs, and corrections separately and merge client-side. |

### 2.4 UI Rendering Mismatches

| ID | Mismatch | UI Location | Description |
|----|----------|-------------|-------------|
| M-13 | **Queue reload merges 3 localStorage sources** | `index.html` L39432–39545 (`reloadVerifierQueuesFromStore`) | Merges localStorage queue + `PATCH_REQUEST_STORE.list()` + `listArtifacts()` — all localStorage. Never queries DB. |
| M-14 | **Verifier review detail tries 3 client sources before fallback** | `index.html` L43870–43920 | Checks `PATCH_REQUEST_STORE.get()` → `getArtifact()` → `verifierQueueState.payloads.find()` — all localStorage. Never calls `GET /patches/{id}`. |
| M-15 | **Correction creation never calls API** | `index.html` (Evidence Viewer correction flow) | Creates corrections in ARTIFACT_STORE (localStorage). Never calls `POST /documents/{doc}/corrections`. |

---

## 3. Migration/Cutover Plan

### 3.1 Overview

The migration moves the Operations View from localStorage-first to DB-first in three phases:

```
Phase 1: DB-First Read Path    → UI reads from DB, falls back to localStorage
Phase 2: DB-First Write Path   → UI writes to DB, caches to localStorage
Phase 3: localStorage Removal  → localStorage code removed, DB is sole store
```

### 3.2 Phase 1: DB-First Read Path

**Goal:** Operations View hydrates from the DB on page load.

**Changes:**
1. On page load / mode switch to Operations View:
   - Call `GET /workspaces/{ws}/operations/queue?queue_status=pending`
   - Populate `verifierQueueState.payloads` from response
   - Update tab counts from response `counts`
2. If API call fails (network error, 401):
   - Fall back to localStorage cache
   - Show "offline / unsynced" banner
3. localStorage continues to be written (dual-write for safety) but is NOT the primary read source

**Feature Flag:** `OPS_VIEW_DB_READ = true` (default off during testing, on after validation)

**Rollback:** Set `OPS_VIEW_DB_READ = false` → reverts to pure localStorage reads

### 3.3 Phase 2: DB-First Write Path

**Goal:** All verifier actions write to DB via API endpoints.

**Changes:**
1. `vrApprove()` → calls `PATCH /patches/{pat_id}` with status transition
2. `vrReject()` → calls `PATCH /patches/{pat_id}` with rejection
3. `updatePayloadStatus()` → calls appropriate API endpoint based on item type
4. RFI custody transitions → calls `PATCH /rfis/{rfi_id}`
5. Correction approvals → calls `PATCH /corrections/{cor_id}`
6. On success: update localStorage cache (dual-write)
7. On failure: show error toast, DO NOT update localStorage

**Feature Flag:** `OPS_VIEW_DB_WRITE = true` (default off during testing)

**Rollback:** Set `OPS_VIEW_DB_WRITE = false` → reverts to pure localStorage writes

### 3.4 Phase 3: localStorage Removal

**Goal:** Remove all legacy localStorage code for the verifier queue.

**Changes:**
1. Remove `verifierQueueState` localStorage persistence
2. Remove `PATCH_REQUEST_STORE` (or convert to server-backed cache)
3. Remove `ARTIFACT_STORE` usage for governance artifacts (keep for non-governance UI state)
4. Remove `saveVerifierQueue()`, `reloadVerifierQueuesFromStore()` functions
5. Remove feature flags (DB is now the only path)

**Prerequisite:** Phase 1 + Phase 2 stable for at least 1 development cycle with no regressions.

### 3.5 One-Time localStorage → DB Migration (Idempotent)

**Purpose:** Existing users may have verifier queue items in localStorage that don't exist in the DB. These need to be migrated.

**Strategy:**

1. On first Operations View load with `OPS_VIEW_DB_READ = true`:
   - Fetch DB queue via API
   - Read localStorage queue via `verifierQueueState.payloads`
   - Identify items in localStorage that are NOT in DB (by `id` cross-reference)
   - If orphaned localStorage items exist, show banner: "Found N items from a previous session. Migrate to server?"
   - On user confirmation, POST each item to the appropriate endpoint:
     - Patches → `POST /workspaces/{ws}/patches`
     - RFIs → `POST /workspaces/{ws}/rfis`
     - Corrections → `POST /documents/{doc}/corrections`
   - Mark migration as complete: `localStorage.setItem('ops_view_migration_done', 'true')`
2. If `ops_view_migration_done` is already set, skip migration check

**Idempotency:** Each POST uses an `Idempotency-Key` header based on the localStorage item ID. The server's idempotency_keys table prevents duplicate creation.

### 3.6 Rollback Strategy

| Phase | Rollback Mechanism | Data Safety |
|-------|-------------------|-------------|
| Phase 1 | Feature flag `OPS_VIEW_DB_READ = false` | localStorage data is still being written; no data loss |
| Phase 2 | Feature flag `OPS_VIEW_DB_WRITE = false` | DB data is preserved; localStorage resumes as primary write target |
| Phase 3 | Cannot easily rollback (localStorage code removed) | Full rollback requires code revert. Only proceed when Phase 1+2 are stable. |

---

## 4. Go/No-Go

### 4.1 Blockers

| Blocker | Severity | Resolution Required |
|---------|----------|-------------------|
| RFI batch-scoping strategy not decided (VER-04) | **HARD BLOCKER** | Must decide: add `batch_id` column to `rfis` OR join through `patches.batch_id`. Required for EP-02, EP-04, EP-05, EP-07. |
| Source-of-truth contract not formally locked | **SOFT BLOCKER** | This document and the Artifact Spec constitute the lock. Stakeholder sign-off needed. |
| `user_capabilities` table design review | **NOT A BLOCKER** | Capability roles (V254_ROLE_MODEL_UPDATE.md) are a future Phase 2 item. Position roles work today. |

### 4.2 Recommendation

**Conditional GO** — pending resolution of the RFI batch-scoping strategy (VER-04).

**Recommended approach for VER-04:** Add `batch_id` column to `rfis` (nullable, additive migration 012). Rationale:
- Simplest query path for Operations View
- No dependency on a `records` table (which doesn't exist yet)
- Backward compatible (nullable, existing rows get NULL)
- Populate from batch context at RFI creation time
- Standalone RFIs (no batch context) have NULL `batch_id` and appear in workspace-level queries only

### 4.3 Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|-----------|
| localStorage data loss during migration | Medium | Low | Phase 3.5 migration is opt-in with user confirmation; dual-write in Phase 1+2 preserves data |
| Breaking existing analyst workflows | High | Very Low | All changes are additive; existing localStorage paths continue until Phase 3 |
| Performance of composite queue endpoint | Low | Low | Three indexed queries + in-memory merge; paginated to 50 items |
| Schema migration risk | Low | Very Low | Single additive column; no destructive changes |
| Feature flag complexity | Medium | Medium | Only 2 flags (`OPS_VIEW_DB_READ`, `OPS_VIEW_DB_WRITE`); clear on/off semantics |

### 4.4 Implementation Order

See `V254_VERIFIER_IMPLEMENTATION_TASKLIST.md` for full dependency-ordered task list.

Summary phases:
1. **Foundation** (P0): Lock decisions, add batch/record filters to existing endpoints, fix batch-scoping bugs
2. **Composite Endpoint** (P1): Workspace corrections list, annotations filters, Operations View queue endpoint
3. **UI Wiring** (P2): Wire vrApprove/vrReject/RFI/corrections to DB, hydrate queue from DB
4. **Cleanup** (P3–P4): SSE filters, localStorage migration utility, remove legacy code

---

*End of V2.54 Verifier Operations View Clarity Phase*
