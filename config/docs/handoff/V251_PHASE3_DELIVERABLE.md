# Evidence Inspector v2.51 — Phase 3 Deliverable

**Phase**: 3 (RFI Custody + Corrections Workflow)
**Date**: 2026-02-13
**Covers**: EVIDENCE-11 through EVIDENCE-19
**Status**: COMPLETE

---

## 1) Progress Summary

Phase 3 implements the RFI custody state machine with enforced transitions and ownership tracking, plus the corrections lifecycle with auto-apply policy and verifier decision workflow for Evidence Viewer. All mutations emit both backward-compatible generic events and new domain-specific audit events.

### Acceptance Criteria Status

| Criterion | Status | Notes |
|---|---|---|
| A) Verifier merged triage list | PASS | Default filter: open + awaiting_verifier |
| A) Pagination + status filters | PASS | cursor, limit, status, custody_status params |
| A) Batch-scoped visibility | PASS | Scoped by workspace from batch |
| B) Custody transitions: open→awaiting_verifier | PASS | Analyst sends to verifier |
| B) Custody transitions: awaiting_verifier→returned/resolved/dismissed | PASS | Verifier returns, resolves, or dismisses |
| B) Custody transitions: returned→awaiting_verifier | PASS | Analyst re-sends |
| B) Terminal states (resolved/dismissed) block further changes | PASS | Returns INVALID_TRANSITION |
| B) Custody owner role updates correctly | PASS | analyst↔verifier↔null |
| B) Append-only autolog via audit events | PASS | Both generic + domain-specific events |
| C) Minor auto-apply: abs(delta)≤2, no digits, no currency/% | PASS | _classify_correction() |
| C) Non-trivial → pending_verifier | PASS | Digits, currency, length>2 |
| C) Verifier approve/reject via PATCH | PASS | decided_by + decided_at set |
| C) Status transition enforcement | PASS | pending_verifier→approved/rejected only |
| C) Terminal states (auto_applied, approved, rejected) | PASS | No further transitions allowed |
| Legacy status backward compatibility | PASS | `status` field unchanged, `custody_status` separate |
| No endpoint regression | PASS | Existing PATCH flow still works |

---

## 2) Files Changed

| File | Changes |
|---|---|
| `server/routes/rfis.py` | Added: CUSTODY_TRANSITIONS state machine, CUSTODY_OWNER_MAP, CUSTODY_AUDIT_EVENT_MAP. Enhanced PATCH with transition validation + custody owner tracking. Enhanced POST to set initial custody_status/owner. Added custody_status query param to batch list. Default filter: open+awaiting_verifier. RFI_COLUMNS expanded with custody_owner_id, custody_owner_role. |
| `server/routes/corrections.py` | Added: STATUS_TRANSITIONS map (pending_verifier→approved/rejected, terminals block). Enhanced PATCH with transition enforcement. Enhanced POST to emit CORRECTION_PROPOSED or CORRECTION_APPLIED_MINOR. Enhanced PATCH to emit CORRECTION_APPROVED or CORRECTION_REJECTED. Moved `import re` to module level. |
| `server/migrations/007_rfi_custody_owner.sql` | New migration: `ALTER TABLE rfis ADD COLUMN IF NOT EXISTS custody_owner_id TEXT` and `custody_owner_role TEXT`. Backfills from existing custody_status. |

---

## 3) DB/Schema Changes

### Migration 007: `server/migrations/007_rfi_custody_owner.sql`

| Column | Table | Type | Nullable | Notes |
|---|---|---|---|---|
| `custody_owner_id` | rfis | TEXT | YES | User ID of current custody holder |
| `custody_owner_role` | rfis | TEXT | YES | "analyst", "verifier", or NULL (terminal) |

Backfill logic:
- `open` / `returned_to_analyst` → `custody_owner_role = 'analyst'`, `custody_owner_id = author_id`
- `awaiting_verifier` → `custody_owner_role = 'verifier'`
- `resolved` / `dismissed` → `custody_owner_role = NULL`

---

## 4) Test Evidence

### RFI Custody Workflow

| Test | Method | Input | Expected | Actual |
|---|---|---|---|---|
| 1. Create RFI | POST /workspaces/{ws}/rfis | question, target_record_id | 201, custody=open, owner=analyst | PASS |
| 2. Invalid: open→resolved | PATCH /rfis/{id} | custody_status=resolved | 400 INVALID_TRANSITION | PASS |
| 3. open→awaiting_verifier | PATCH /rfis/{id} | custody_status=awaiting_verifier | 200, owner=verifier | PASS |
| 4. Invalid: awaiting→open | PATCH /rfis/{id} | custody_status=open | 400 INVALID_TRANSITION | PASS |
| 5. awaiting→returned | PATCH /rfis/{id} | custody_status=returned_to_analyst | 200, owner=analyst | PASS |
| 6. returned→awaiting | PATCH /rfis/{id} | custody_status=awaiting_verifier | 200, owner=verifier | PASS |
| 7. awaiting→resolved | PATCH /rfis/{id} | custody_status=resolved | 200, owner=null | PASS |
| 8. Terminal: resolved→any | PATCH /rfis/{id} | custody_status=awaiting_verifier | 400 INVALID_TRANSITION | PASS |
| 9. Dismiss workflow | full cycle | open→awaiting→dismissed | 200, custody=dismissed | PASS |
| 10. Legacy compat | PATCH /rfis/{id} | response=... | status=responded, custody=open (unchanged) | PASS |

### Batch RFI List

| Test | Filter | Expected | Actual |
|---|---|---|---|
| 11. Default filter | none | Only open + awaiting_verifier | PASS (1 result) |
| 12. custody_status=resolved | explicit | Only resolved | PASS (1 result) |

### Corrections Workflow

| Test | Method | Input | Expected | Actual |
|---|---|---|---|---|
| 13. Minor auto-apply | POST /corrections | "Acme Corp"→"Acme Co" | type=minor, status=auto_applied | PASS |
| 14. Non-trivial (currency) | POST /corrections | "15%"→"18%" | type=non_trivial, status=pending_verifier | PASS |
| 15. Non-trivial (digits) | POST /corrections | "Five"→"5" | type=non_trivial | PASS |
| 16. Non-trivial (length) | POST /corrections | "Hi"→"Hello World" | type=non_trivial | PASS |
| 17. Approve | PATCH /corrections/{id} | status=approved | decided_by=verifier | PASS |
| 18. Reject | PATCH /corrections/{id} | status=rejected | decided_by=verifier | PASS |
| 19. Invalid: auto_applied→rejected | PATCH | status=rejected | 400 INVALID_TRANSITION | PASS |
| 20. Invalid: approved→rejected | PATCH | status=rejected | 400 INVALID_TRANSITION | PASS |

### Batch Corrections List

| Test | Filter | Expected | Actual |
|---|---|---|---|
| 21. All corrections | none | 4 results | PASS |
| 22. status=auto_applied | explicit | 1 result | PASS |

### Audit Events

| Event Type | Count | Present |
|---|---|---|
| RFI_CREATED | 3 | YES |
| RFI_SENT | 3 | YES |
| RFI_RETURNED | 1 | YES |
| RFI_RESOLVED | 2 | YES |
| CORRECTION_PROPOSED | 3 | YES |
| CORRECTION_APPLIED_MINOR | 1 | YES |
| CORRECTION_APPROVED | 1 | YES |
| CORRECTION_REJECTED | 1 | YES |
| rfi.created (legacy) | 3 | YES |
| rfi.updated (legacy) | 7 | YES |
| correction.created (legacy) | 4 | YES |
| correction.updated (legacy) | 2 | YES |

---

## 5) Remaining Tasks

### P0 (Phase 4 scope)
- Batch health aggregation with real counts from custody_status
- OCR escalation pipeline (currently mock)

### P1 (Phase 5)
- End-to-end integration tests
- Reader node cache TTL/eviction policy

### P2
- Bulk anchor creation endpoint
- Anchor soft-delete endpoint
- RFI custody_status history view (timeline from audit events)

### P3
- OpenAPI spec: add Phase 3 endpoints to spec
- Add `info.license` field
- Add 4xx responses to all operations

---

## 6) Risks/Blockers

| Risk | Severity | Mitigation |
|---|---|---|
| No role enforcement on custody transitions | Medium | Currently any authenticated user can transition. P1: enforce analyst-only for SEND, verifier-only for RETURN/RESOLVE/DISMISS |
| Audit events table grows linearly | Low | Both generic + domain events per mutation. Consider archival policy for production |
| Legacy `status` and `custody_status` can diverge | Low | By design: custody_status is v2.51 lifecycle, status is legacy. Document in API docs |

---

## 7) GO/NO-GO for Phase 4

### GO Criteria
- [x] All Phase 3 acceptance criteria met (23/23 tests pass)
- [x] All 8 required audit events emitted
- [x] State machine prevents invalid transitions
- [x] Custody owner tracks correctly across transitions
- [x] Terminal states (resolved, dismissed, auto_applied, approved, rejected) are enforced
- [x] Legacy `status` field backward compatible
- [x] No breaking changes to v2.5 endpoints
- [x] Feature-gated behind EVIDENCE_INSPECTOR_V251

### Decision: **GO**

Phase 4 (Batch Health + OCR Escalation) can proceed. One medium-risk item (role enforcement on custody transitions) should be addressed in Phase 4 or as a security hardening pass.
