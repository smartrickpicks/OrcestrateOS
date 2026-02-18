# v2.51 Evidence Inspector — Pre-Code Deliverables

## A) Coupling Conflict Report

### Conflict 1: ULID Prefix Registry
- **File:** `server/ulid.py`, line 5-9
- **Issue:** `VALID_PREFIXES` does not include `anc_` (anchor) or `cor_` (correction). Calling `generate_id("anc_")` or `generate_id("cor_")` will raise `ValueError`.
- **Mitigation:** Add `"anc_"` and `"cor_"` to the `VALID_PREFIXES` frozenset. No existing code is affected — purely additive.

### Conflict 2: RFI Status Enum Mismatch
- **File:** `server/routes/rfis.py`, line 17
- **Issue:** Existing `ALLOWED_STATUSES = ("open", "responded", "closed")`. Spec requires custody statuses: `open`, `awaiting_verifier`, `returned_to_analyst`, `resolved`, `dismissed`. Direct replacement breaks existing v2.5 clients that send `"responded"` or `"closed"`.
- **Mitigation:** Add a `custody_status` column to the `rfis` table (nullable TEXT, default NULL). New v2.51 endpoints use `custody_status`. Existing v2.5 `status` column remains unchanged. A mapping function bridges the two: `open→open`, `responded→awaiting_verifier`, `closed→resolved`. The `GET /batches/{id}/rfis?status=` endpoint filters on `custody_status` when present, falling back to `status`. This preserves backward compatibility while enabling the new lifecycle.

### Conflict 3: Document Route Expansion
- **File:** `server/routes/documents.py`, lines 36-296
- **Issue:** New sub-resource routes (`/documents/{id}/reader-nodes`, `/documents/{id}/anchors`, `/documents/{id}/corrections`, `/documents/{id}/ocr-escalations`) could be added to this file, but would make it unwieldy.
- **Mitigation:** Create dedicated route modules: `server/routes/reader_nodes.py`, `server/routes/anchors.py`, `server/routes/corrections.py`, `server/routes/ocr_escalations.py`. Each gets its own router with the same `/api/v2.5` prefix. This follows the existing pattern where each resource has its own file.

### Conflict 4: Batch Route Expansion
- **File:** `server/routes/batches.py`, lines 39-303
- **Issue:** New sub-resource routes (`/batches/{id}/rfis`, `/batches/{id}/corrections`, `/batches/{id}/health`) need to be added. The existing `batches.py` already handles CRUD for batches.
- **Mitigation:** Add the batch-scoped RFI/correction list endpoints to the existing `rfis.py` and `corrections.py` route modules respectively (since they're logically RFI and correction operations scoped to a batch). Create a new `server/routes/batch_health.py` for the health aggregation endpoint.

### Conflict 5: Router Registration
- **File:** `server/pdf_proxy.py`, lines 84-102
- **Issue:** All new route modules must be imported and registered with `app.include_router()`.
- **Mitigation:** Add imports and `include_router` calls for the 5 new modules: `reader_nodes`, `anchors`, `corrections`, `batch_health`, `ocr_escalations`. Follows exact same pattern as existing registrations.

### Conflict 6: Audit Event Types
- **File:** `server/audit.py`, lines 10-38
- **Issue:** No conflict — `emit_audit_event` accepts arbitrary `event_type` strings. New event types (`anchor.created`, `correction.created`, `correction.updated`, `rfi.custody_changed`, `ocr_escalation.created`, `batch.health_queried`) work without changes.
- **Mitigation:** None needed. Existing audit infrastructure is fully extensible.

### Conflict 7: Feature Flag Gating
- **File:** None (new)
- **Issue:** All new v2.51 endpoints must be gated behind `EVIDENCE_INSPECTOR_V251` feature flag. No feature flag infrastructure exists.
- **Mitigation:** Create `server/feature_flags.py` with a simple `is_enabled(flag_name)` check against environment variables. Each new endpoint starts with a flag check and returns 404 with `FEATURE_DISABLED` error if the flag is not set.

### Conflict 8: No DB Migration Collision
- **File:** `server/migrations/` (next number: 005)
- **Issue:** None — migration numbering is sequential and automated.
- **Mitigation:** Create `005_evidence_inspector_v251.sql` with all new tables and column additions.

---

## B) Implementation Plan (Dependency Order)

### Phase 1 — Foundation: Schema + Feature Flag + IDs
Dependencies: None (base layer)

| ID | Task | Files | Depends On |
|----|------|-------|------------|
| EVIDENCE-01 | Add `anc_`, `cor_` to VALID_PREFIXES | `server/ulid.py` | — |
| EVIDENCE-02 | Create feature flag module | `server/feature_flags.py` | — |
| EVIDENCE-03 | Write migration 005: `anchors`, `corrections`, `reader_node_cache`, `ocr_escalations` tables; add `custody_status` column to `rfis` | `server/migrations/005_evidence_inspector_v251.sql` | — |
| EVIDENCE-04 | Run migration, verify schema | — | EVIDENCE-03 |
| EVIDENCE-05 | Backfill `custody_status` from `status` for existing RFIs | Migration SQL | EVIDENCE-04 |
| EVIDENCE-06 | Create route module skeletons with feature flag guards | All new route files | EVIDENCE-02 |

### Phase 2 — 3-Pane + Reader Shell (Document Sub-Resources)
Dependencies: Phase 1

| ID | Task | Files | Depends On |
|----|------|-------|------------|
| EVIDENCE-07 | `GET /documents/{id}/reader-nodes` — generate/cache reader nodes from PDF text, return with quality_flag | `server/routes/reader_nodes.py` | EVIDENCE-06 |
| EVIDENCE-08 | `POST /documents/{id}/anchors` — create anchor with ULID + fingerprint dedup | `server/routes/anchors.py` | EVIDENCE-01, EVIDENCE-06 |
| EVIDENCE-09 | `GET /documents/{id}/anchors` — list anchors with pagination | `server/routes/anchors.py` | EVIDENCE-08 |
| EVIDENCE-10 | Register reader_nodes + anchors routers in pdf_proxy.py | `server/pdf_proxy.py` | EVIDENCE-07, EVIDENCE-08 |

### Phase 3 — RFI Custody + Batch Triage
Dependencies: Phase 1

| ID | Task | Files | Depends On |
|----|------|-------|------------|
| EVIDENCE-11 | Extend `PATCH /rfis/{id}` to accept `custody_status` transitions | `server/routes/rfis.py` | EVIDENCE-05 |
| EVIDENCE-12 | `GET /batches/{id}/rfis?status=` — filter by custody_status with fallback | `server/routes/rfis.py` | EVIDENCE-11 |
| EVIDENCE-13 | Verifier batch triage default: `open` + `awaiting_verifier` | `server/routes/rfis.py` | EVIDENCE-12 |
| EVIDENCE-14 | Audit events for custody transitions (`rfi.custody_changed`) | `server/routes/rfis.py` | EVIDENCE-11 |

### Phase 4 — Corrections + Admin Queue
Dependencies: Phase 2, Phase 3

| ID | Task | Files | Depends On |
|----|------|-------|------------|
| EVIDENCE-15 | `POST /documents/{id}/corrections` — create correction with minor/non-trivial classification | `server/routes/corrections.py` | EVIDENCE-06, EVIDENCE-08 |
| EVIDENCE-16 | Minor correction auto-apply policy: abs(length_delta)<=2, no digits, no currency/percent | `server/routes/corrections.py` | EVIDENCE-15 |
| EVIDENCE-17 | `PATCH /corrections/{id}` — approve/reject transitions | `server/routes/corrections.py` | EVIDENCE-15 |
| EVIDENCE-18 | `GET /batches/{id}/corrections?status=` — list with status filter | `server/routes/corrections.py` | EVIDENCE-15 |
| EVIDENCE-19 | Register corrections router in pdf_proxy.py | `server/pdf_proxy.py` | EVIDENCE-15 |

### Phase 5 — Health + OCR + Smoke Tests
Dependencies: Phase 3, Phase 4

| ID | Task | Files | Depends On |
|----|------|-------|------------|
| EVIDENCE-20 | `GET /batches/{id}/health` — aggregate counts (rfis_open, corrections_pending, mojibake_suspect_docs, etc.) | `server/routes/batch_health.py` | EVIDENCE-12, EVIDENCE-18 |
| EVIDENCE-21 | `POST /documents/{id}/ocr-escalations` — mock endpoint with audit | `server/routes/ocr_escalations.py` | EVIDENCE-06 |
| EVIDENCE-22 | Register batch_health + ocr_escalations routers | `server/pdf_proxy.py` | EVIDENCE-20, EVIDENCE-21 |
| EVIDENCE-23 | Smoke tests: anchor idempotency, reader fallback flags, RFI custody transitions | `scripts/test_evidence_v251.sh` | All above |
| EVIDENCE-24 | Smoke tests: correction policy split, batch health counts, audit event emissions | `scripts/test_evidence_v251.sh` | All above |
| EVIDENCE-25 | Update replit.md with v2.51 scope | `replit.md` | All above |

---

## C) GO/NO-GO Check

### GO ✅ — Conditional

**Conditions met:**
1. ✅ All new endpoints are additive — no existing v2.5 routes are modified or removed
2. ✅ Existing envelope format (`data`/`meta`/`error`) is reused unchanged
3. ✅ ULID + prefix pattern extends cleanly
4. ✅ Audit infrastructure (`emit_audit_event`) is fully extensible
5. ✅ Migration runner supports sequential numbered SQL files
6. ✅ Feature flag gating keeps v2.51 invisible until enabled

**Conditions requiring confirmation:**
1. ⚠️ **RFI status compatibility** — Recommend `custody_status` column approach. If the team prefers full status replacement, this becomes a BREAKING change requiring a migration + client update coordinated release. **Decision needed before Phase 3.**
2. ⚠️ **Reader node source** — Spec says "use available extracted/OCR text." The existing `/api/pdf/text` endpoint in `pdf_proxy.py` extracts text from remote PDFs via PyMuPDF. Reader nodes can call this internally. Confirm: should reader nodes be cached in DB or generated on-demand only?

**Recommendation:** Proceed with Phase 1 immediately. The `custody_status` column approach resolves the RFI compatibility issue without breaking changes. Reader node caching follows the spec's cache-by-key directive.

### Risk Register

| Risk | Severity | Mitigation |
|------|----------|------------|
| RFI status break | HIGH | custody_status column (dual-field) |
| Feature flag leak (endpoint visible without flag) | MEDIUM | Shared guard function, tested in smoke |
| Anchor fingerprint collision | LOW | sha256 is collision-resistant; UNIQUE constraint catches duplicates |
| Reader node generation latency | MEDIUM | Cache in DB keyed by (document_id, source_pdf_hash, ocr_version) |
| Migration 005 failure on existing data | LOW | All new columns nullable, all new tables independent |
