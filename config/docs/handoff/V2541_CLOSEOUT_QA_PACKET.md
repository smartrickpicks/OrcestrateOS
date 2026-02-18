# V2.54.1 — Closeout QA Packet

**Version:** v2.54.1  
**Date:** 2026-02-17  
**Status:** GO for production cutover (staged)

---

## 1. P0–P3 Acceptance Matrix

### 1.1 P0 — Foundation Fixes

| ID | Test | Expected | Actual | Status |
|----|------|----------|--------|--------|
| P0-1 | DB write URL matches backend route (`PATCH /patches/{id}`) | 200 on valid PATCH | 200 | PASS |
| P0-2 | Strict mode: local state updates only after DB success | No optimistic local write before DB response | Verified | PASS |
| P0-3 | Workspace role enforcement on operations queue | `require_role()` called, 403 for non-members | 403 returned | PASS |
| P0-4 | Sandbox role-switch rehydration: queue clears on role change | Queue re-fetches from DB on role switch | Verified | PASS |

### 1.2 P1 — RFI/Correction DB Writes

| ID | Test | Expected | Actual | Status |
|----|------|----------|--------|--------|
| P1-1 | `opsDbWriteRfiStatus()` sends PATCH to `/rfis/{id}` | 200 with version bump | 200, version incremented | PASS |
| P1-2 | `opsDbWriteCorrectionStatus()` sends PATCH to `/corrections/{id}` | 200 with version bump | 200, version incremented | PASS |
| P1-3 | Unified `updatePayloadStatus` dispatcher routes by type | patch→patches, rfi→rfis, correction→corrections | Correct routing | PASS |
| P1-4 | Strict mode for RFI/correction writes | Local update after DB success only | Verified | PASS |

### 1.3 P2 — Drive Batch Dedupe

| ID | Test | Expected | Actual | Status |
|----|------|----------|--------|--------|
| P2-1 | `source = "drive"` accepted in batch creation | 201 Created | 201 | PASS |
| P2-2 | Missing `drive_file_id` for drive source returns 422 | 422 VALIDATION_ERROR | 422 | PASS |
| P2-3 | Missing `revision_id` and `modified_time` returns 422 | 422 VALIDATION_ERROR | 422 | PASS |
| P2-4 | Duplicate drive_file_id + revision_marker returns 200 with existing batch | 200 with reuse flag | 200 | PASS |
| P2-5 | Audit event emitted for dedupe hit | `batch.dedupe_hit` in audit_events | Recorded | PASS |
| P2-6 | Partial unique index prevents concurrent duplicate inserts | DB-level uniqueness enforced | Index created | PASS |

### 1.4 P3 — Role-Scoped Visibility + Custody Matrix

| ID | Test | Expected | Actual | Status |
|----|------|----------|--------|--------|
| P3-1 | Analyst `/patches` sees own only | `author_id = user_id` for all results | all_own=True | PASS |
| P3-2 | Analyst `/rfis` sees own only | `author_id = user_id` for all results | all_own=True | PASS |
| P3-3 | Analyst `/corrections` sees own only | `created_by = user_id` for all results | all_own=True | PASS |
| P3-4 | Verifier sees workspace-wide patches | count >= analyst count | Verified | PASS |
| P3-5 | Admin sees full workspace patches | count >= verifier count | Verified | PASS |
| P3-6 | Non-member returns 401/403 | 401 or 403 | 401 | PASS |
| P3-7 | No auth returns 401 | 401 | 401 | PASS |
| P3-8 | Custody: open → awaiting_verifier (analyst) | 200 + version bump | 200, v2 | PASS |
| P3-9 | Custody: awaiting_verifier → returned_to_analyst (verifier) | 200 + version bump | 200, v3 | PASS |
| P3-10 | Disallowed transition → 409 INVALID_TRANSITION | 409 | 409 | PASS |
| P3-11 | Disallowed role → 403 ROLE_NOT_ALLOWED | 403 | 403 | PASS |
| P3-12 | Stale version → 409 STALE_VERSION | 409 | 409 | PASS |
| P3-13 | Audit events for custody transitions | RFI_SENT, RFI_RETURNED present | Present | PASS |
| P3-14 | Queue counts role-consistent | admin >= analyst | Verified | PASS |
| P3-15 | Filters/pagination work | 200 | 200 | PASS |
| P3-16 | P0/P1/P2 regression check | Upload 201, Queue 200 | Both correct | PASS |

---

## 2. P4 Release-Readiness Checks

| # | Check | Status | Evidence |
|---|-------|--------|----------|
| 1 | Release runbook includes migration order, prereqs, rollback | PASS | `V2541_RELEASE_RUNBOOK.md` §2–5 |
| 2 | Cutover plan includes staged flag sequence + entry/exit criteria | PASS | `V2541_CUTOVER_PLAN.md` §2–3 |
| 3 | Monitoring guardrails include metrics + thresholds + playbook | PASS | `V2541_MONITORING_GUARDRAILS.md` §1–3 |
| 4 | Closeout QA packet includes consolidated P0–P4 evidence | PASS | This document §1 |
| 5 | Flags default-safe behavior documented | PASS | `V2541_RELEASE_RUNBOOK.md` §4 |
| 6 | Rollback executable without schema rollback | PASS | `V2541_RELEASE_RUNBOOK.md` §5, §8 |
| 7 | Clear owner/actions for incident scenarios | PASS | `V2541_MONITORING_GUARDRAILS.md` §5 |
| 8 | Changelog accurately reflects implemented behavior | PASS | `CHANGELOG.md` v2.54.1 section |
| 9 | API notes match current routes and error contracts | PASS | `CHANGELOG.md` API Contract Notes |
| 10 | Known deferred items listed explicitly | PASS | §3 below |

---

## 3. Known Deferred Items

| Item | Reason | Target |
|------|--------|--------|
| Prometheus metrics export | Not needed for initial rollout; logging sufficient | Post-v2.54.1 |
| Client-side version refresh on 409 | Frontend change; not in P4 scope | v2.55 |
| Correction custody transition matrix | Corrections use simpler approve/reject flow | v2.55 if needed |
| Automated acceptance test suite (CI) | Manual smoke procedure sufficient for staged rollout | v2.55 |
| localStorage-to-DB data migration tool | Not needed — DB and localStorage can coexist during transition | If requested |
| Operations queue pagination | Current limit=200 sufficient for known workloads | v2.55 if needed |

---

## 4. API Contract Summary

### 4.1 Unchanged Contracts (v2.5 stable)

| Method | Endpoint | Contract |
|--------|----------|----------|
| GET | `/api/v2.5/workspaces/{ws}/patches` | Returns patches (now role-filtered) |
| GET | `/api/v2.5/workspaces/{ws}/rfis` | Returns RFIs (now role-filtered) |
| GET | `/api/v2.5/workspaces/{ws}/corrections` | Returns corrections (now role-filtered) |
| GET | `/api/v2.5/workspaces/{ws}/operations/queue` | Returns unified queue (now role-filtered) |
| POST | `/api/v2.5/workspaces/{ws}/patches` | Creates patch |
| POST | `/api/v2.5/workspaces/{ws}/rfis` | Creates RFI |
| POST | `/api/v2.5/workspaces/{ws}/batches` | Creates batch (now accepts `source: "drive"`) |
| PATCH | `/api/v2.5/patches/{id}` | Updates patch status/fields |
| PATCH | `/api/v2.5/rfis/{id}` | Updates RFI (now with custody transition enforcement) |

### 4.2 New/Changed Error Codes

| Code | HTTP | When |
|------|------|------|
| `INVALID_TRANSITION` | 409 | RFI custody transition not in allowed matrix |
| `ROLE_NOT_ALLOWED` | 403 | User role cannot perform this custody transition |
| `STALE_VERSION` | 409 | Optimistic concurrency conflict (version mismatch) |
| `VALIDATION_ERROR` | 422 | Drive batch missing required metadata fields |
| `FORBIDDEN` | 403 | User not a member of the workspace |

---

## 5. Production Recommendation

### GO — with staged rollout conditions

**Recommendation:** GO for production cutover via staged flag sequence.

**Conditions:**
1. Apply migrations 012 + 013 before enabling any flags
2. Follow staged rollout: Stage A (read-only) → 24h soak → Stage B (read+write)
3. Monitor key metrics per `V2541_MONITORING_GUARDRAILS.md` thresholds
4. Keep rollback path ready: both flags can be set to `false` for immediate revert

**Confidence level:** High — 16/16 P3 acceptance tests pass, all P0–P2 items verified with no regressions, rollback is flag-only (no schema changes required).

**Risk assessment:**
- Low risk: Migrations are additive, flags default safe, analyst filtering is a security improvement
- Medium risk: First production use of DB-backed operations queue — mitigated by staged rollout
- Mitigation: Flag rollback takes < 2 minutes, preserves all data

---

## 6. Sign-off

| Role | Name | Date | Decision |
|------|------|------|----------|
| Developer | — | 2026-02-17 | GO |
| Reviewer | — | — | — |
| Ops | — | — | — |
