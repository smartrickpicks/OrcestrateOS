# V2.54 Verifier Implementation Task List

**Version:** 2.54  
**Date:** 2026-02-17  
**Status:** LOCKED — Clarity Phase  
**Scope:** Sequenced task list with dependencies, acceptance criteria, and priority assignments  

---

## 1. Task List

### Phase 0: Documentation Lock

| ID | Priority | Type | Description | Depends On | Est. |
|----|----------|------|-------------|------------|------|
| VER-01 | P0 | DOC | Lock source-of-truth contract: copy `V254_ANNOTATION_LAYER_ARTIFACT_SPEC.md` §4 into `docs/decisions/DECISION_ANNOTATION_LAYER_PRECEDENCE.md` | — | 0.5h |
| VER-02 | P0 | DOC | Lock naming standard: search-replace "Verifier Dashboard" → "Operations View" in codebase comments and UI labels | — | 1h |
| VER-03 | P0 | DOC | Add EP-07 (`/operations/queue`) to `docs/api/openapi.yaml` | — | 1h |

### Phase 1: Foundation (P0)

| ID | Priority | Type | Description | Depends On | Est. |
|----|----------|------|-------------|------------|------|
| VER-04 | P0 | DECISION | Decide RFI batch-scoping strategy: add `batch_id` column to `rfis` (recommended) vs. JOIN through `patches.batch_id` | — | — |
| VER-05 | P0 | MIGRATION | Create migration 012: add `batch_id` column to `rfis` table (nullable TEXT FK → batches.id) | VER-04 | 0.5h |
| VER-06 | P0 | MIGRATION | Create migration 012 (cont): add indexes `idx_rfis_batch(workspace_id, batch_id)`, `idx_rfis_custody(workspace_id, custody_status)`, `idx_patches_batch(workspace_id, batch_id)`, `idx_patches_record(workspace_id, record_id)` | VER-05 | 0.5h |
| VER-10 | P0 | IMPLEMENT | Add `record_id` and `batch_id` query params to `GET /workspaces/{ws}/patches` | — | 1h |
| VER-11 | P0 | IMPLEMENT | Fix `GET /batches/{bat}/rfis` batch-scoping bug (rfis.py L500–501) | VER-05 | 1h |
| VER-12 | P0 | IMPLEMENT | Fix `GET /batches/{bat}/health` RFI batch-scoping bug (batch_health.py L40–51) | VER-05 | 0.5h |
| VER-13 | P0 | IMPLEMENT | Add `batch_id` query param to `GET /workspaces/{ws}/rfis` | VER-05 | 1h |

### Phase 2: Composite Endpoint (P1)

| ID | Priority | Type | Description | Depends On | Est. |
|----|----------|------|-------------|------------|------|
| VER-14 | P1 | IMPLEMENT | Add `GET /workspaces/{ws}/corrections` workspace-level correction list endpoint | — | 2h |
| VER-15 | P1 | IMPLEMENT | Add `target_type` and `target_id` query params to `GET /workspaces/{ws}/annotations` | — | 1h |
| VER-16 | P1 | IMPLEMENT | Create `GET /workspaces/{ws}/operations/queue` composite endpoint (new file: `server/routes/operations_queue.py`) | VER-10, VER-11, VER-13, VER-14 | 3h |
| VER-17 | P1 | DOC | Update `docs/api/openapi.yaml` with all new/modified endpoint schemas | VER-10–VER-16 | 1.5h |

### Phase 3: UI Wiring (P2)

| ID | Priority | Type | Description | Depends On | Est. |
|----|----------|------|-------------|------------|------|
| VER-20 | P2 | IMPLEMENT | Wire `vrApprove()` to call `PATCH /patches/{pat_id}` with status=`Verifier_Approved` + version. Handle 200/409/403. | VER-10 | 2h |
| VER-21 | P2 | IMPLEMENT | Wire `vrReject()` to call `PATCH /patches/{pat_id}` with status=`Rejected` + version + rejection reason in metadata. Handle 200/409/403. | VER-10 | 1.5h |
| VER-22 | P2 | IMPLEMENT | Wire `renderVerifierTriage()` to hydrate from `GET /operations/queue` instead of localStorage. Add feature flag `OPS_VIEW_DB_READ`. Fallback to localStorage on network error with "offline" banner. | VER-16 | 3h |
| VER-23 | P2 | IMPLEMENT | Wire RFI custody transitions in Operations View to call `PATCH /rfis/{rfi_id}`. Handle 200/409/403. | — | 2h |
| VER-24 | P2 | IMPLEMENT | Wire correction approve/reject in Operations View to call `PATCH /corrections/{cor_id}`. Handle 200/409/403. | — | 1.5h |
| VER-25 | P2 | IMPLEMENT | Wire verifier review detail page to load from `GET /patches/{pat_id}` instead of localStorage lookup. | VER-20 | 2h |
| VER-26 | P2 | IMPLEMENT | Add feature flag `OPS_VIEW_DB_WRITE` to gate all write-path changes (VER-20 through VER-25). | VER-20–VER-25 | 1h |

### Phase 4: Migration & Cleanup (P3–P4)

| ID | Priority | Type | Description | Depends On | Est. |
|----|----------|------|-------------|------------|------|
| VER-30 | P3 | IMPLEMENT | Add batch-scoped SSE filter params to `/events/stream`: `batch_id`, `resource_type` query params | — | 2h |
| VER-31 | P3 | IMPLEMENT | Implement one-time localStorage → DB migration utility (idempotent, user-prompted) | VER-16, VER-22 | 3h |
| VER-32 | P4 | IMPLEMENT | Remove legacy localStorage verifier queue code (`saveVerifierQueue`, `reloadVerifierQueuesFromStore`, `verifierQueueState` localStorage persistence) | VER-31 | 2h |
| VER-33 | P4 | IMPLEMENT | Remove feature flags (`OPS_VIEW_DB_READ`, `OPS_VIEW_DB_WRITE`) — make DB the sole path | VER-32 | 0.5h |

### Phase 5: Security & Testing

| ID | Priority | Type | Description | Depends On | Est. |
|----|----------|------|-------------|------------|------|
| VER-40 | P0 | AUDIT | Verify no self-approval bypass: server enforces `self_approval_check` (patches.py L358–365), confirm UI pre-check cannot be circumvented | VER-20 |
| VER-41 | P1 | AUDIT | Verify workspace isolation: all new/modified endpoints reject cross-workspace access (403 or 404) | VER-10–VER-16 |
| VER-42 | P1 | AUDIT | Verify optimistic concurrency: all PATCH endpoints check version, return 409 on stale | VER-20–VER-24 |
| VER-50 | P2 | TEST | Integration: verifier approves patch → DB status = `Verifier_Approved` → audit_event emitted → SSE event pushed | VER-20 |
| VER-51 | P2 | TEST | Integration: verifier rejects patch → DB status = `Rejected` → audit_event logged | VER-21 |
| VER-52 | P2 | TEST | Integration: RFI custody `awaiting_verifier` → `resolved` with verifier role check | VER-23 |
| VER-53 | P2 | TEST | Integration: correction `pending_verifier` → `approved` with role check + `decided_by` set | VER-24 |
| VER-54 | P2 | TEST | Concurrency: two verifiers load same patch; first approves (200); second approves with stale version (409) | VER-20 |
| VER-55 | P2 | TEST | Self-approval: analyst-authored patch → analyst is also verifier → approve attempt → 403 `SELF_APPROVAL_BLOCKED` | VER-20, VER-40 |
| VER-56 | P2 | TEST | Workspace isolation: user in ws_A calls `PATCH /patches/{pat_in_ws_B}` → 403 | VER-41 |

---

## 2. Dependency Graph

```
VER-04 (Decision: RFI batch-scoping)
  └── VER-05 (Migration: batch_id on rfis)
        └── VER-06 (Migration: indexes)
              ├── VER-11 (Fix batch RFI scoping)
              ├── VER-12 (Fix batch health RFI counts)
              └── VER-13 (Add batch_id to RFI list)

VER-10 (Add record_id/batch_id to patches list) ──┐
VER-11 ────────────────────────────────────────────┤
VER-13 ────────────────────────────────────────────┤
VER-14 (Workspace corrections list) ───────────────┤
                                                   └── VER-16 (Composite queue endpoint)
                                                         └── VER-22 (DB-first read)
                                                               └── VER-31 (localStorage migration)
                                                                     └── VER-32 (Remove legacy code)
                                                                           └── VER-33 (Remove flags)

VER-10 ── VER-20 (Wire vrApprove) ── VER-25 (Wire review detail)
       └─ VER-21 (Wire vrReject)
VER-20──VER-26 (Feature flags)
```

---

## 3. Acceptance Criteria

### 3.1 P0 Criteria (Must Pass Before Phase 2)

| AC-ID | Task | Criterion | Verification Method |
|-------|------|-----------|---------------------|
| AC-01 | VER-05 | Migration 012 runs idempotently; `rfis.batch_id` column exists and is nullable | `\d rfis` in psql |
| AC-02 | VER-06 | All 4 recommended indexes exist | `\di` in psql |
| AC-03 | VER-10 | `GET /workspaces/{ws}/patches?record_id=rec_X` returns only patches targeting `rec_X` | curl + assert count |
| AC-04 | VER-10 | `GET /workspaces/{ws}/patches?batch_id=bat_X` returns only patches in batch `bat_X` | curl + assert count |
| AC-05 | VER-11 | `GET /batches/{bat}/rfis` returns only RFIs with `batch_id = bat` (not all workspace RFIs) | curl + count comparison vs. `GET /workspaces/{ws}/rfis` |
| AC-06 | VER-12 | `GET /batches/{bat}/health` → `rfi_count` reflects only the target batch | curl + manual count verification |
| AC-07 | VER-13 | `GET /workspaces/{ws}/rfis?batch_id=bat_X` returns batch-scoped RFIs | curl + assert |
| AC-08 | VER-40 | Self-approval attempt returns 403 `SELF_APPROVAL_BLOCKED` (server-side) | curl with author's JWT |

### 3.2 P1 Criteria (Must Pass Before Phase 3)

| AC-ID | Task | Criterion | Verification Method |
|-------|------|-----------|---------------------|
| AC-10 | VER-14 | `GET /workspaces/{ws}/corrections?status=pending_verifier` returns workspace corrections | curl + assert |
| AC-11 | VER-14 | `GET /workspaces/{ws}/corrections?batch_id=bat_X` returns batch-scoped corrections | curl + assert |
| AC-12 | VER-15 | `GET /workspaces/{ws}/annotations?target_type=patch&target_id=pat_X` returns only matching annotations | curl + assert |
| AC-13 | VER-16 | `GET /workspaces/{ws}/operations/queue?queue_status=pending` returns unified list of patches + RFIs + corrections | curl + verify all 3 types present |
| AC-14 | VER-16 | Response includes `counts` object with all 4 queue statuses | curl + assert counts shape |
| AC-15 | VER-16 | `batch_id` filter narrows results to a single batch | curl + compare filtered vs. unfiltered |
| AC-16 | VER-41 | Cross-workspace request returns 403 or 404 | curl with wrong workspace JWT |

### 3.3 P2 Criteria (Must Pass Before Phase 4)

| AC-ID | Task | Criterion | Verification Method |
|-------|------|-----------|---------------------|
| AC-20 | VER-20 | `vrApprove()` sends `PATCH /patches/{id}` with `{status: "Verifier_Approved", version: N}` | Network inspector |
| AC-21 | VER-20 | On 409 STALE_VERSION, UI shows "modified by someone else" toast and refetches | Simulate concurrent edit |
| AC-22 | VER-20 | On 403 SELF_APPROVAL_BLOCKED, UI shows error toast and does NOT change local state | Test with author's session |
| AC-23 | VER-21 | `vrReject()` requires notes (non-empty) and sends `PATCH /patches/{id}` with `{status: "Rejected"}` | Network inspector |
| AC-24 | VER-22 | On page load, Operations View calls `GET /operations/queue` (not localStorage) | Network inspector + console logs |
| AC-25 | VER-22 | On network error, falls back to localStorage with "offline" banner | Disable network, reload |
| AC-26 | VER-23 | RFI custody transition calls `PATCH /rfis/{id}` | Network inspector |
| AC-27 | VER-24 | Correction approval calls `PATCH /corrections/{id}` | Network inspector |
| AC-28 | VER-42 | Stale version (409) during any approval shows user-friendly message and refreshes | Simulate concurrent edit |

### 3.4 P3–P4 Criteria

| AC-ID | Task | Criterion | Verification Method |
|-------|------|-----------|---------------------|
| AC-30 | VER-31 | Migration utility detects orphaned localStorage items and prompts user | Clear DB, populate localStorage, reload |
| AC-31 | VER-31 | Migration is idempotent (running twice doesn't create duplicates) | Run twice, check DB counts |
| AC-32 | VER-32 | After legacy code removal, no references to `srr_verifier_queue_v1` remain in codebase | grep verification |
| AC-33 | VER-33 | Feature flags removed; DB is sole read/write path | grep verification |

---

## 4. Estimated Effort Summary

| Phase | Tasks | Estimated Hours |
|-------|-------|----------------|
| Phase 0: Doc Lock | VER-01 to VER-03 | 2.5h |
| Phase 1: Foundation | VER-04 to VER-13 | 4.5h |
| Phase 2: Composite | VER-14 to VER-17 | 7.5h |
| Phase 3: UI Wiring | VER-20 to VER-26 | 13h |
| Phase 4: Cleanup | VER-30 to VER-33 | 7.5h |
| Phase 5: Security/Test | VER-40 to VER-56 | 8h |
| **Total** | | **43h** |

---

## 5. Implementation Sequence (Recommended Order)

1. VER-01 → VER-04 (lock decisions, make batch-scoping decision)
2. VER-05 → VER-06 (migration)
3. VER-10, VER-11, VER-12, VER-13 (parallel: endpoint fixes)
4. VER-14, VER-15 (parallel: new/extended endpoints)
5. VER-16 (composite queue — depends on 3+4)
6. VER-40, VER-41 (security audit checkpoint)
7. VER-20, VER-21, VER-23, VER-24 (parallel: wire UI actions to DB)
8. VER-22 (DB-first read hydration)
9. VER-25, VER-26 (review detail + feature flags)
10. VER-42 (concurrency audit)
11. VER-50–VER-56 (integration tests)
12. VER-30 (SSE filters)
13. VER-31 (localStorage migration utility)
14. VER-32 → VER-33 (legacy removal)
15. VER-02, VER-03, VER-17 (docs catch-up — can be done in parallel throughout)

---

*End of V2.54 Verifier Implementation Task List*
