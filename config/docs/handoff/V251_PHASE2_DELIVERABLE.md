# Evidence Inspector v2.51 — Phase 2 Deliverable

**Phase**: 2 (Reader + Anchors)
**Date**: 2026-02-13
**Covers**: EVIDENCE-07, EVIDENCE-08, EVIDENCE-09, EVIDENCE-10
**Status**: COMPLETE

---

## 1) Progress Summary

Phase 2 implements the core Reader Node Cache and Anchor subsystems with deterministic identifiers, fingerprint-based deduplication, and full audit event emission for Evidence Viewer.

### Acceptance Criteria Status

| Criterion | Status | Notes |
|---|---|---|
| A) GET reader-nodes with deterministic node_id | PASS | `rn_` + SHA-256(doc_id\|page\|block)[:24] |
| A) quality_flag exact enum | PASS | ok, suspect_mojibake, unreadable, missing_text_layer |
| A) no text layer -> empty nodes + missing_text_layer | PASS | Verified in test 1 and test 4 |
| A) DB cache key (document_id, source_pdf_hash, ocr_version) | PASS | UNIQUE constraint on table |
| B) POST anchors with selected_text_hash + anchor_fingerprint | PASS | Both SHA-256, server-computed |
| B) Idempotent duplicate (200 return existing) | PASS | Same fingerprint -> 200 + existing anchor |
| C) GET anchors pagination | PASS | Cursor-based, limit 1-200, field_id/page_number filters |
| D) Smart Highlight payload contract | PASS | node_id, char_start, char_end, selected_text, field_id, field_key |

### Phase 1 Closeout

| Item | Status |
|---|---|
| OpenAPI structural validation | PASS — 0 errors, 30 warnings (cosmetic) |
| Paths normalized under `paths:` | PASS — 16 paths moved from components |
| `nullable` → 3.1.0 `[type, 'null']` | PASS — 0 occurrences of deprecated `nullable:` |
| Unresolved $refs fixed | PASS — 144 $refs all resolve |
| Duplicate schemas removed | PASS — 43 unique schemas |

---

## 2) Changes Made

### Modified Files

| File | Changes |
|---|---|
| `server/routes/reader_nodes.py` | Full rewrite: deterministic `_deterministic_node_id()`, quality auto-detection `_detect_quality()`, PUT upsert endpoint with UPSERT SQL, audit events |
| `server/routes/anchors.py` | Enhanced: added `_compute_selected_text_hash()`, input validation (node_id, char_start, char_end, selected_text required), `selected_text_hash` in INSERT/SELECT, `field_id`/`page_number` query filters, LSP fix |
| `server/routes/corrections.py` | LSP fix: `params: list` type annotation |
| `server/migrations/006_anchors_selected_text_hash.sql` | New migration: `ALTER TABLE anchors ADD COLUMN IF NOT EXISTS selected_text_hash TEXT` |
| `docs/api/openapi.yaml` | Structural normalization (16 paths moved), nullable fixes, Meta ref fixes, PUT reader-nodes endpoint added, selected_text_hash added to Anchor schema |

### New Endpoints

| Method | Path | Description |
|---|---|---|
| PUT | `/api/v2.5/documents/{doc_id}/reader-nodes` | Upsert reader node cache with deterministic node_ids |

### Enhanced Endpoints

| Method | Path | Enhancement |
|---|---|---|
| GET | `/api/v2.5/documents/{doc_id}/reader-nodes` | Now returns `cached: true/false` flag |
| POST | `/api/v2.5/documents/{doc_id}/anchors` | Now computes `selected_text_hash`, validates required fields |
| GET | `/api/v2.5/documents/{doc_id}/anchors` | Added `field_id` and `page_number` query filters |

---

## 3) Test Results

### Test 1: GET reader-nodes (no cache)
```
GET /api/v2.5/documents/{doc_id}/reader-nodes
→ 200 { quality_flag: "missing_text_layer", cached: false, nodes: [] }
```

### Test 2: PUT reader-nodes (upsert)
```
PUT /api/v2.5/documents/{doc_id}/reader-nodes
Body: { source_pdf_hash: "sha_abc", ocr_version: "v1", page_count: 2, nodes: [...] }
→ 200 { quality_flag: "ok", cached: true, nodes: [{ node_id: "rn_a27cd8ab...", ... }] }
```

### Test 3: GET reader-nodes (cache hit)
```
GET /api/v2.5/documents/{doc_id}/reader-nodes?source_pdf_hash=sha_abc&ocr_version=v1
→ 200 { quality_flag: "ok", cached: true, nodes: [3 nodes] }
```

### Test 4: GET reader-nodes (cache miss)
```
GET /api/v2.5/documents/{doc_id}/reader-nodes?source_pdf_hash=nonexistent
→ 200 { quality_flag: "missing_text_layer", cached: false, nodes: [] }
```

### Test 5: POST anchor (create)
```
POST /api/v2.5/documents/{doc_id}/anchors
Body: { node_id: "rn_...", char_start: 0, char_end: 19, selected_text: "RECORDING AGREEMENT", page_number: 1 }
→ 201 { id: "anc_...", anchor_fingerprint: "decf6c6b...", selected_text_hash: "68c1e443..." }
```

### Test 6: POST anchor (idempotent dedup)
```
POST /api/v2.5/documents/{doc_id}/anchors  (same payload as Test 5)
→ 200 { id: same_anchor_id }  -- Returns existing, no duplicate created
```

### Test 7: GET anchors (pagination)
```
GET /api/v2.5/documents/{doc_id}/anchors?limit=1
→ 200 { data: [1 anchor], meta: { pagination: { has_more: true, cursor: "anc_..." } } }

GET /api/v2.5/documents/{doc_id}/anchors?limit=1&cursor=anc_...
→ 200 { data: [1 different anchor] }
```

### Test 8: Validation errors
```
POST .../anchors { char_start: 0, char_end: 10, selected_text: "t" }
→ 400 VALIDATION_ERROR "node_id is required"

POST .../anchors { node_id: "x", selected_text: "t" }
→ 400 VALIDATION_ERROR "char_start and char_end are required"
```

### Test 9: Deterministic node_id
```
PUT reader-nodes (same doc + page 1 + block 0, different text)
→ Same node_id as original: TRUE
```

### Test 10: Audit events
```
anchor.created ✓
reader_node_cache.upserted ✓
```

---

## 4) Remaining Tasks

### P0 (Phase 3 scope)
- RFI custody_status workflow with state machine transitions
- Correction status lifecycle (pending_verifier → approved/rejected)

### P1 (Phase 4-5)
- Batch health aggregation with real counts
- OCR escalation pipeline (currently mock)
- End-to-end integration tests

### P2
- Reader node cache TTL/eviction policy
- Bulk anchor creation endpoint
- Anchor soft-delete endpoint

### P3
- OpenAPI file structural consolidation (full reorder deferred)
- Add `info.license` field to OpenAPI spec
- Add 4xx responses to all operations

---

## 5) Risks/Blockers

| Risk | Severity | Mitigation |
|---|---|---|
| reader_node_cache grows unbounded | Low | P2: add TTL/eviction policy |
| selected_text_hash column not backfilled for existing anchors | Low | Migration 006 adds nullable column; backfill on next access |
| No rate limiting on PUT reader-nodes | Medium | Large node payloads could be expensive; consider size limits |

---

## 6) GO/NO-GO for Phase 3

### GO Criteria
- [x] All Phase 2 acceptance criteria met
- [x] All endpoints feature-gated
- [x] All mutations emit audit events
- [x] Deterministic IDs verified
- [x] OpenAPI validated (0 errors)
- [x] No breaking changes to v2.5

### Decision: **CONDITIONAL GO**

Phase 3 (RFI Custody + Corrections workflow) can proceed. One P2 item (reader node cache size limits) should be addressed before production deployment but does not block Phase 3 development.
