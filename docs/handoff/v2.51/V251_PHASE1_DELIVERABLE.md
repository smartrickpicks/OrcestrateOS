# Evidence Inspector v2.51 — Phase 1 Deliverable

**Date:** 2026-02-13
**Phase:** 1 — Foundation (Schema + Feature Flag + IDs + Route Skeletons)
**Status:** COMPLETE

---

## 1) Progress Summary

Phase 1 delivers the foundational infrastructure for Evidence Viewer v2.51:

| Task ID | Description | Status |
|---------|-------------|--------|
| EVIDENCE-01 | Add `anc_`, `cor_`, `oce_` to ULID prefix registry | DONE |
| EVIDENCE-02 | Create feature flag module (`server/feature_flags.py`) | DONE |
| EVIDENCE-03 | Write migration 005: 4 new tables + 1 new column | DONE |
| EVIDENCE-04 | Run migration, verify schema | DONE |
| EVIDENCE-05 | Backfill `custody_status` from `status` for existing RFIs | DONE (in migration SQL) |
| EVIDENCE-06 | Create route module skeletons with feature flag guards | DONE |
| — | Register all 5 new routers in `pdf_proxy.py` | DONE |
| — | Extend `rfis.py` with custody_status PATCH + batch listing | DONE |
| — | Set `EVIDENCE_INSPECTOR_V251=true` env var | DONE |
| — | Update `replit.md` with v2.51 scope | DONE |

All v2.51 endpoints return proper auth (401), feature-gate (404 FEATURE_DISABLED), and resource-not-found (404 NOT_FOUND) responses. The server starts clean with zero errors.

---

## 2) Files Changed + Line References

### New Files (5 route modules + 1 infra + 1 migration)

| File | Lines | Purpose |
|------|-------|---------|
| `server/feature_flags.py` | 36 | Env-based feature flag with cache + `require_evidence_inspector()` guard |
| `server/migrations/005_evidence_inspector_v251.sql` | 109 | 4 tables + `rfis.custody_status` column + backfill + indexes |
| `server/routes/reader_nodes.py` | 80 | `GET /documents/{id}/reader-nodes` — cache lookup + missing_text_layer fallback |
| `server/routes/anchors.py` | 198 | `POST + GET /documents/{id}/anchors` — fingerprint dedup + pagination |
| `server/routes/corrections.py` | 346 | `POST /documents/{id}/corrections` + `PATCH /corrections/{id}` + `GET /batches/{id}/corrections` |
| `server/routes/batch_health.py` | 101 | `GET /batches/{id}/health` — aggregate counts |
| `server/routes/ocr_escalations.py` | 104 | `POST /documents/{id}/ocr-escalations` — mock endpoint |

### Modified Files

| File | Change | Lines Affected |
|------|--------|----------------|
| `server/ulid.py` | Added `"anc_"`, `"cor_"`, `"oce_"` to `VALID_PREFIXES` | L5-9 |
| `server/pdf_proxy.py` | Added 5 router imports + `include_router()` calls | L60-64, L108-112 |
| `server/routes/rfis.py` | Added `custody_status` to columns, PATCH support, `GET /batches/{id}/rfis` endpoint | L24, L247-253, L319-320, L370-395 |
| `replit.md` | Added v2.51 section with scope, phases, endpoints, decision locks | L73-100 |

---

## 3) Migration SQL + Rollback Note

### Migration: `server/migrations/005_evidence_inspector_v251.sql`

**Forward (applied automatically on startup):**

1. `ALTER TABLE rfis ADD COLUMN IF NOT EXISTS custody_status TEXT` — additive, nullable
2. `UPDATE rfis SET custody_status = ...` — backfill mapping: `open→open`, `responded→awaiting_verifier`, `closed→resolved`
3. `CREATE TABLE IF NOT EXISTS anchors` — document text anchors with fingerprint UNIQUE constraint
4. `CREATE TABLE IF NOT EXISTS corrections` — field-level corrections with auto-classify
5. `CREATE TABLE IF NOT EXISTS reader_node_cache` — cached text extraction, UNIQUE on `(document_id, source_pdf_hash, ocr_version)`
6. `CREATE TABLE IF NOT EXISTS ocr_escalations` — mock OCR pipeline stub
7. 8 indexes on foreign keys and frequently-filtered columns

**Rollback SQL (manual, NOT auto-executed):**
```sql
DROP TABLE IF EXISTS ocr_escalations;
DROP TABLE IF EXISTS corrections;
DROP TABLE IF EXISTS anchors;
DROP TABLE IF EXISTS reader_node_cache;
ALTER TABLE rfis DROP COLUMN IF EXISTS custody_status;
```

**Safety notes:**
- All `CREATE TABLE IF NOT EXISTS` — idempotent, safe to re-run
- All `ADD COLUMN IF NOT EXISTS` — idempotent
- No existing columns modified, no existing constraints altered
- `corrections.anchor_id` FK → `anchors.id` requires anchors dropped last (order above is safe)

---

## 4) API Route Skeletons Registered (Feature-Gated)

All endpoints live under `/api/v2.5/` namespace and use the standard `ok/data/meta` envelope.

| Method | Path | Module | Auth | Feature Gate | Audit Event |
|--------|------|--------|------|--------------|-------------|
| GET | `/documents/{id}/reader-nodes` | reader_nodes.py | EITHER | Yes | — (read-only) |
| POST | `/documents/{id}/anchors` | anchors.py | BEARER | Yes | `anchor.created` |
| GET | `/documents/{id}/anchors` | anchors.py | EITHER | Yes | — (read-only) |
| POST | `/documents/{id}/corrections` | corrections.py | BEARER | Yes | `correction.created` |
| PATCH | `/corrections/{id}` | corrections.py | BEARER | Yes | `correction.updated` |
| GET | `/batches/{id}/corrections` | corrections.py | EITHER | Yes | — (read-only) |
| GET | `/batches/{id}/rfis` | rfis.py | EITHER | Yes | — (read-only) |
| GET | `/batches/{id}/health` | batch_health.py | EITHER | Yes | — (read-only) |
| POST | `/documents/{id}/ocr-escalations` | ocr_escalations.py | BEARER | Yes | `ocr_escalation.created` |

**Feature gate behavior:** When `EVIDENCE_INSPECTOR_V251` env var is not `true`, all endpoints return:
```json
{
  "error": {
    "code": "FEATURE_DISABLED",
    "message": "Evidence Viewer v2.51 is not enabled. Set EVIDENCE_INSPECTOR_V251=true to activate."
  }
}
```

**Existing v2.5 RFI changes (NOT feature-gated — backward compatible):**
- `PATCH /rfis/{id}` now accepts optional `custody_status` field (additive, does not affect existing `status` flow)
- `GET /batches/{id}/rfis?status=` filters on `custody_status` with fallback to `status`

---

## 5) OpenAPI / Canonical Docs Update

See `docs/api/openapi.yaml` — v2.51 additive schemas and endpoints appended.

**New schemas added to `components/schemas`:**
- `Anchor` — id, document_id, anchor_fingerprint, node_id, char_start/end, selected_text, field_id/key, page_number
- `AnchorCreate`, `AnchorResponse`, `AnchorCollection`
- `Correction` — id, document_id, anchor_id, rfi_id, field_id/key, original_value, corrected_value, correction_type, status
- `CorrectionCreate`, `CorrectionUpdate`, `CorrectionResponse`, `CorrectionCollection`
- `ReaderNodeCache` — id, document_id, source_pdf_hash, ocr_version, quality_flag, nodes[], page_count, cached
- `ReaderNodeResponse`
- `OcrEscalation` — id, document_id, escalation_type, status, requested_by, resolved_by, _mock, _note
- `OcrEscalationResponse`
- `BatchHealth` — batch_id, counts{}, blockers[], updated_at
- `BatchHealthResponse`
- `Rfi` — id, document_id, status (v2.5), custody_status (v2.51 additive), version, metadata
- `RfiCollection`

**New path entries (9 operations):** All under `/api/v2.5/` namespace, tagged `[Evidence Viewer]`.

**Known structural note:** Path entries are appended after the Drive integration paths, following the same established pattern in the file. A full file restructure to consolidate all paths under a single `paths:` block is deferred to a future housekeeping pass.

**New ID prefixes registered in `server/ulid.py`:**
- `anc_` — Anchor
- `cor_` — Correction
- `oce_` — OCR Escalation

---

## 6) Risks / Blockers + GO/NO-GO

### Decision Locks Confirmed ✅

| Decision | Lock Status | Implementation |
|----------|-------------|----------------|
| RFI status strategy | LOCKED — additive `custody_status` | Column added, backfilled, dual-read in batch endpoint |
| Reader node caching | LOCKED — persist in DB | `reader_node_cache` table with `(doc_id, pdf_hash, ocr_version)` unique key |
| Quality flag values | LOCKED — `ok\|suspect_mojibake\|unreadable\|missing_text_layer` | Stored in `quality_flag` column, fallback returns `missing_text_layer` |
| Correction auto-classify | LOCKED — `abs(len_delta)<=2 AND no digits AND no currency/pct` | `_classify_correction()` in corrections.py |

### Risk Register

| Risk | Severity | Status | Mitigation |
|------|----------|--------|------------|
| RFI backward compat break | HIGH | MITIGATED | `custody_status` is additive, `status` untouched |
| Feature flag leak | MEDIUM | MITIGATED | Shared `require_evidence_inspector()` guard on every endpoint |
| Migration failure on existing data | LOW | MITIGATED | All IF NOT EXISTS, nullable columns, backfill is idempotent |
| LSP warnings (6 diagnostics) | LOW | ACCEPTED | Type hints for psycopg2 cursor — no runtime impact |
| Reader node generation latency | MEDIUM | DEFERRED TO PHASE 2 | Cache layer built; actual PDF→nodes pipeline is Phase 2 work |

### Blockers

None. All Phase 1 tasks complete, all decision locks confirmed.

### GO/NO-GO for Phase 2

## **GO** ✅

**Evidence:**
1. Server starts clean — all 5 migrations applied, zero errors
2. All 9 new endpoints respond correctly (auth gates, feature gates, 404s tested)
3. Feature flag toggles correctly (`EVIDENCE_INSPECTOR_V251=true` active)
4. No breaking changes to existing v2.5 routes
5. `custody_status` backfill applied to existing RFIs
6. All mutation endpoints emit audit events
7. Optimistic concurrency (version + 409 STALE_VERSION) on corrections
8. Anchor fingerprint dedup prevents duplicates (UNIQUE constraint)
9. OpenAPI spec updated with all v2.51 additive resources

**Phase 2 scope (Reader + Anchors):**
- Wire `GET /documents/{id}/reader-nodes` to actual PDF text extraction via PyMuPDF
- Populate `reader_node_cache` on first read with quality detection
- Build reader node→anchor selection pipeline
- Frontend 3-pane Evidence Viewer shell (if applicable)
