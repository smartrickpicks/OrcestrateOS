# v2.51 Suggested Fields + Alias Builder — Audit Report

> Phase 4: Verification Report

---

## 1. Files Changed

| File | Change Type | Task ID |
|------|-------------|---------|
| `server/migrations/008_suggested_fields.sql` | NEW | SUGGEST-01 |
| `server/ulid.py` | MODIFIED — added 4 prefixes: `glt_`, `gla_`, `sgr_`, `sug_` | SUGGEST-02 |
| `server/routes/suggestions.py` | NEW — suggestion runs + suggestions CRUD | SUGGEST-03 |
| `server/routes/glossary.py` | NEW — glossary terms + aliases CRUD | SUGGEST-04 |
| `server/suggestion_engine.py` | NEW — heuristic generator + fuzzy matching | SUGGEST-05 |
| `server/pdf_proxy.py` | MODIFIED — registered 2 new routers | SUGGEST-06 |
| `ui/viewer/index.html` | MODIFIED — Sync Suggestions tab, panel, CSS, JS | SUGGEST-07 |
| `docs/handoff/V251_SUGGESTED_FIELDS_DESIGN.md` | NEW — Phase 1+2 design doc | — |
| `docs/handoff/V251_SUGGESTED_FIELDS_AUDIT.md` | NEW — this file | SUGGEST-08 |

## 2. SQL Migration Summary

**Migration 008** creates 4 new tables (no ALTER on existing tables):

| Table | PK Prefix | Rows at deploy | Foreign Keys |
|-------|-----------|----------------|--------------|
| `glossary_terms` | `glt_` | 0 | workspaces |
| `glossary_aliases` | `gla_` | 0 | workspaces, glossary_terms, users |
| `suggestion_runs` | `sgr_` | 0 | workspaces, documents, users |
| `suggestions` | `sug_` | 0 | workspaces, suggestion_runs, documents, glossary_terms, users |

**Indexes**: 11 indexes total (4 PK + 7 secondary).

**Unique constraints**:
- `glossary_terms(workspace_id, field_key) WHERE deleted_at IS NULL`
- `glossary_aliases(workspace_id, normalized_alias) WHERE deleted_at IS NULL`

**Rollback**: `DROP TABLE suggestions, suggestion_runs, glossary_aliases, glossary_terms CASCADE;`

## 3. Endpoint Examples

### POST /api/v2.5/documents/{document_id}/suggestion-runs

```bash
curl -X POST http://localhost:5000/api/v2.5/documents/doc_XXXX/suggestion-runs \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json"
```

**Response 201:**
```json
{
  "data": {
    "id": "sgr_01JMGXYZ...",
    "workspace_id": "ws_SEED...",
    "document_id": "doc_XXXX",
    "status": "completed",
    "total_suggestions": 12,
    "created_at": "2026-02-14T17:00:00Z",
    "completed_at": "2026-02-14T17:00:01Z",
    "created_by": "usr_...",
    "metadata": {}
  },
  "meta": { "request_id": "req_...", "timestamp": "..." }
}
```

### GET /api/v2.5/documents/{document_id}/suggestions

```bash
curl http://localhost:5000/api/v2.5/documents/doc_XXXX/suggestions?status=pending&limit=50 \
  -H "Authorization: Bearer <token>"
```

**Response 200:**
```json
{
  "data": [
    {
      "id": "sug_01JMG...",
      "source_field": "Pmt_Freq",
      "suggested_term_id": "glt_01JMG...",
      "match_score": 0.85,
      "match_method": "fuzzy",
      "status": "pending",
      "candidates": [
        {"term_id": "glt_01JMG...", "score": 0.85, "method": "fuzzy"},
        {"term_id": "glt_01JMH...", "score": 0.62, "method": "fuzzy"}
      ]
    }
  ],
  "meta": { "pagination": { "cursor": null, "has_more": false, "limit": 50 } }
}
```

### PATCH /api/v2.5/suggestions/{suggestion_id}

```bash
curl -X PATCH http://localhost:5000/api/v2.5/suggestions/sug_01JMG... \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"status": "accepted", "version": 1}'
```

**Response 200:**
```json
{
  "data": {
    "id": "sug_01JMG...",
    "status": "accepted",
    "resolved_by": "usr_...",
    "resolved_at": "2026-02-14T17:05:00Z",
    "version": 2,
    "alias_id": "gla_01JMG..."
  },
  "meta": { "request_id": "req_...", "timestamp": "..." }
}
```

### GET /api/v2.5/glossary/terms

```bash
curl "http://localhost:5000/api/v2.5/glossary/terms?query=payment&limit=20" \
  -H "Authorization: Bearer <token>"
```

### POST /api/v2.5/glossary/aliases

```bash
curl -X POST http://localhost:5000/api/v2.5/glossary/aliases \
  -H "Authorization: Bearer <token>" \
  -H "Content-Type: application/json" \
  -d '{"term_id": "glt_01JMG...", "alias": "Pmt Freq"}'
```

**409 on duplicate:**
```json
{
  "error": {
    "code": "DUPLICATE_ALIAS",
    "message": "Alias 'Pmt Freq' already exists in this workspace",
    "details": {
      "existing_alias_id": "gla_...",
      "existing_term_id": "glt_...",
      "existing_field_key": "Payment_Frequency__c"
    }
  }
}
```

## 4. Acceptance Criteria Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | Migration 008 creates all 4 tables without errors | PASS |
| 2 | Migration is idempotent (CREATE TABLE IF NOT EXISTS) | PASS |
| 3 | ULID prefixes `glt_`, `gla_`, `sgr_`, `sug_` registered | PASS |
| 4 | POST suggestion-runs triggers heuristic engine | PASS |
| 5 | Fuzzy matching returns top 3 candidates | PASS |
| 6 | Exact match scores 1.0 | PASS |
| 7 | Keyword scoring uses document type keywords | PASS |
| 8 | Accept creates glossary_aliases row | PASS |
| 9 | Duplicate alias returns 409 with existing details | PASS |
| 10 | Optimistic concurrency on suggestions (version field) | PASS |
| 11 | Audit events emitted on all mutations | PASS |
| 12 | GET glossary/terms supports query, category, cursor, limit | PASS |
| 13 | Frontend "Sync" button added to grid float controls | PASS |
| 14 | Sync panel toggles open/close | PASS |
| 15 | Suggestions grouped by match type (exact/fuzzy/keyword/none) | PASS |
| 16 | Accept/Reject buttons with immediate UI update | PASS |
| 17 | Demo fallback when no document ID available | PASS |
| 18 | `/api/v2.5` envelope shape preserved | PASS |
| 19 | No existing routes or UI broken | PASS |
| 20 | No destructive refactors | PASS |

## 5. Smoke Test Steps

1. Start server: `python -m uvicorn server.pdf_proxy:app --host 0.0.0.0 --port 5000`
2. Verify migration applied: check logs for "Migration 008_suggested_fields.sql applied successfully"
3. Verify tables exist: `SELECT table_name FROM information_schema.tables WHERE table_name IN ('glossary_terms', 'glossary_aliases', 'suggestion_runs', 'suggestions');` — should return 4 rows
4. Hit health endpoint: `curl http://localhost:5000/api/v2.5/health` — should return `{"status": "ok"}`
5. Hit glossary terms (unauthenticated): `curl http://localhost:5000/api/v2.5/glossary/terms` — should return 401
6. Open UI, load data, click "Sync" button in grid controls — panel should open
7. Click "Run Suggestions" — in demo mode, shows sample suggestions with Accept/Reject buttons
8. Click Accept on a suggestion — status changes to green "accepted" badge
9. Click Reject on a suggestion — status changes to red "rejected" badge

## 6. Known Gaps and Follow-ups

| Gap | Priority | Notes |
|-----|----------|-------|
| Glossary term seeding | P1 | No terms seeded yet — the suggestion engine needs glossary_terms rows to produce real matches. Needs a seed script or import from `field_meta.json`. |
| Document `column_headers` metadata | P1 | The engine reads `metadata.column_headers` from the documents table. Documents need to have this populated during import for the engine to find source fields. |
| Glossary term search in accept flow | P2 | Frontend doesn't yet show a glossary picker when accepting — it uses the suggested term. Could let the user override with a search. |
| Batch-level suggestion runs | P2 | Current flow is per-document. Could add a batch-level endpoint that runs suggestions across all documents in a batch. |
| Suggestion deduplication across runs | P3 | Multiple runs for the same document create duplicate suggestions. Could add upsert logic keyed on `(document_id, source_field)`. |
| `_escHtml` reuse | P3 | Frontend `_escHtml` function duplicates existing patterns — could be consolidated. |

---

*Created: February 2026 — Orchestrate OS v2.51*
