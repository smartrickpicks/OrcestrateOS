# v2.51 Suggested Fields + Alias Builder — Design Doc

> Phase 1: Doc + Phase 2: Clarity

---

## 1. Current-State Inventory

### 1.1 Glossary Tables

**Status: None exist in database.**

The frontend has a glossary UI (CSS classes `srr-glossary-*`, portal tooltip `#glossary-portal-tooltip`) driven entirely by a client-side JSON cache (`field_meta.json` loaded at runtime). There are no `glossary_terms` or `glossary_aliases` tables in the 18-table core schema (`001_core_tables.sql`).

### 1.2 Suggestion-Related Patterns

**Status: No suggestion infrastructure exists.**

No suggestion tables, endpoints, or frontend components. The closest analog is the `triage_items` table (issues surfaced by preflight/semantic/system_pass sources) and the `signals` table (cell-level flags). Both follow the standard ULID-keyed, workspace-scoped pattern.

### 1.3 Triage / Registry UX Reuse Points

The frontend has several patterns we can reuse:

| Pattern | Location | Reuse for |
|---------|----------|-----------|
| Lane cards (Pre-Flight, Semantic, Patch Review) | Triage Analytics header | Add "Sync Suggestions" as 4th lane |
| Nested parent/child table | Pre-Flight Contract Health | Group suggestions by type |
| Accept/Reject buttons | Verifier Triage payload queue | Accept/Reject suggestion actions |
| Glossary picker + search | `srr-glossary-search`, `srr-glossary-list` | Alias target selection |
| Status badges | Triage items, patches | Suggestion status (pending/accepted/rejected) |

### 1.4 Audit Emitter Usage

Well-established pattern in `server/audit.py`:

```python
emit_audit_event(cur, workspace_id, event_type, actor_id,
                 resource_type, resource_id, detail, ...)
```

Used consistently across all 16+ route files. Event types follow `resource.action` naming (e.g., `document.created`, `patch.submitted`). All mutations emit audit events inside the same transaction.

---

## 2. Proposed Additive Changes

### 2.1 New Database Tables (Migration 008)

#### `glossary_terms`
Canonical field definitions. Mirrors what `field_meta.json` provides but persisted in the database.

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | ULID prefix `glt_` |
| workspace_id | TEXT FK → workspaces | Workspace scoped |
| field_key | TEXT NOT NULL | Canonical field name (e.g., `Payment_Frequency__c`) |
| display_name | TEXT | Human-readable label |
| description | TEXT | Field definition |
| data_type | TEXT | string, number, date, picklist, etc. |
| category | TEXT | Grouping category (financial, identity, etc.) |
| is_required | BOOLEAN DEFAULT FALSE | Whether field is required |
| created_at | TIMESTAMPTZ | Standard |
| updated_at | TIMESTAMPTZ | Standard |
| deleted_at | TIMESTAMPTZ | Soft delete |
| version | INTEGER DEFAULT 1 | Optimistic concurrency |
| metadata | JSONB | Extensible |

**Unique constraint**: `(workspace_id, field_key)` where `deleted_at IS NULL`.

#### `glossary_aliases`
Maps alternate names to canonical terms.

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | ULID prefix `gla_` |
| workspace_id | TEXT FK → workspaces | Workspace scoped |
| term_id | TEXT FK → glossary_terms | Which canonical term this aliases to |
| alias | TEXT NOT NULL | The alias string (as seen in source data) |
| normalized_alias | TEXT NOT NULL | Lowercased, trimmed, collapsed whitespace |
| source | TEXT DEFAULT 'manual' | 'manual', 'suggestion', 'import' |
| created_by | TEXT FK → users | Who created the alias |
| created_at | TIMESTAMPTZ | Standard |
| deleted_at | TIMESTAMPTZ | Soft delete |
| metadata | JSONB | Extensible |

**Unique constraint**: `(workspace_id, normalized_alias)` where `deleted_at IS NULL`. This ensures one alias resolves to exactly one canonical term per workspace.

#### `suggestion_runs`
Tracks each execution of the suggestion generator against a document.

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | ULID prefix `sgr_` |
| workspace_id | TEXT FK → workspaces | Workspace scoped |
| document_id | TEXT FK → documents | Which document was analyzed |
| status | TEXT | 'running', 'completed', 'failed' |
| total_suggestions | INTEGER DEFAULT 0 | How many suggestions generated |
| created_at | TIMESTAMPTZ | Standard |
| completed_at | TIMESTAMPTZ | When the run finished |
| created_by | TEXT FK → users | Who triggered the run |
| metadata | JSONB | Config snapshot, timing, etc. |

#### `suggestions`
Individual field mapping suggestions.

| Column | Type | Notes |
|--------|------|-------|
| id | TEXT PK | ULID prefix `sug_` |
| workspace_id | TEXT FK → workspaces | Workspace scoped |
| run_id | TEXT FK → suggestion_runs | Which run produced this |
| document_id | TEXT FK → documents | Source document |
| source_field | TEXT NOT NULL | The field name found in the source data |
| suggested_term_id | TEXT FK → glossary_terms | Best-match canonical term (nullable if no match) |
| match_score | REAL | 0.0–1.0 confidence score |
| match_method | TEXT | 'exact', 'fuzzy', 'keyword', 'none' |
| status | TEXT DEFAULT 'pending' | 'pending', 'accepted', 'rejected', 'dismissed' |
| resolved_by | TEXT FK → users | Who accepted/rejected |
| resolved_at | TIMESTAMPTZ | When resolved |
| candidates | JSONB | Top 3 candidates `[{term_id, score, method}]` |
| created_at | TIMESTAMPTZ | Standard |
| version | INTEGER DEFAULT 1 | Optimistic concurrency |
| metadata | JSONB | Extensible |

### 2.2 New API Endpoints

All under `/api/v2.5`, using standard envelope responses.

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/documents/{document_id}/suggestion-runs` | POST | Trigger a new suggestion run |
| `/documents/{document_id}/suggestions` | GET | List suggestions for a document |
| `/suggestions/{suggestion_id}` | PATCH | Accept/reject a suggestion |
| `/glossary/terms` | GET | Search canonical glossary terms |
| `/glossary/aliases` | POST | Create a new alias mapping |

### 2.3 Frontend UI Changes

Add a **"Sync Suggestions"** tab to the grid header (alongside existing tabs like "Evidence Viewer"). When active:

1. **Run Suggestions button** — Triggers POST to create a suggestion run
2. **Grouped suggestion list** — Suggestions grouped by match type (exact, fuzzy, keyword, unmatched)
3. **Per-suggestion row**: source field name, best match term, confidence score, Accept/Reject buttons
4. **Accept flow**: Accept creates a `glossary_aliases` row linking the source field to the canonical term
5. **Reject flow**: Marks suggestion as rejected (can be re-run later)
6. **Status indicators**: pending (yellow), accepted (green), rejected (red), dismissed (gray)

---

## 3. Phase 2 — Clarity Confirmations

### 3.1 Endpoint Contracts

#### POST `/api/v2.5/documents/{document_id}/suggestion-runs`

```
Request: {} (empty body or optional config)
Response 201: {
  "data": { "id": "sgr_...", "document_id": "doc_...", "status": "completed",
            "total_suggestions": 12, "created_at": "...", "completed_at": "..." },
  "meta": { "request_id": "req_...", "timestamp": "..." }
}
```

Runs synchronously (no external services). The generator scans document metadata/section columns, compares against glossary_terms, and creates suggestion rows.

#### GET `/api/v2.5/documents/{document_id}/suggestions`

```
Query params: ?status=pending&cursor=...&limit=50
Response 200: {
  "data": [ { "id": "sug_...", "source_field": "Pmt_Freq",
              "suggested_term_id": "glt_...", "match_score": 0.82,
              "match_method": "fuzzy", "status": "pending",
              "candidates": [...] } ],
  "meta": { "pagination": {...}, ... }
}
```

#### PATCH `/api/v2.5/suggestions/{suggestion_id}`

```
Request: { "status": "accepted", "version": 1 }
  — or: { "status": "accepted", "version": 1, "selected_term_id": "glt_..." }
Response 200: { "data": { ...updated suggestion... }, "meta": {...} }
```

On accept: if `selected_term_id` differs from `suggested_term_id`, use the override. Automatically creates a `glossary_aliases` row.

#### GET `/api/v2.5/glossary/terms`

```
Query params: ?query=payment&category=financial&limit=20
Response 200: {
  "data": [ { "id": "glt_...", "field_key": "Payment_Frequency__c",
              "display_name": "Payment Frequency", ... } ],
  "meta": { "pagination": {...}, ... }
}
```

#### POST `/api/v2.5/glossary/aliases`

```
Request: { "term_id": "glt_...", "alias": "Pmt Freq" }
Response 201: {
  "data": { "id": "gla_...", "term_id": "glt_...", "alias": "Pmt Freq",
            "normalized_alias": "pmt freq", "source": "manual" },
  "meta": {...}
}
```

Returns 409 if `normalized_alias` already exists in the workspace.

### 3.2 Optimistic Concurrency

- `suggestions` table has a `version` column; PATCH requires `version` in body
- `glossary_terms` table has a `version` column for future term editing
- `glossary_aliases` and `suggestion_runs` are insert-only / append-only; no concurrency needed

### 3.3 Audit Event Names

| Event Type | Trigger | Payload |
|------------|---------|---------|
| `suggestion_run.created` | POST suggestion-runs | `{document_id, total_suggestions}` |
| `suggestion.accepted` | PATCH accept | `{source_field, term_id, alias_id}` |
| `suggestion.rejected` | PATCH reject | `{source_field, reason}` |
| `glossary_alias.created` | POST aliases (or via accept) | `{term_id, alias, normalized_alias}` |
| `glossary_term.created` | Term seeding/import | `{field_key, display_name}` |

### 3.4 Alias Uniqueness Strategy

`normalized_alias` = `LOWER(TRIM(REGEXP_REPLACE(alias, '\s+', ' ', 'g')))`.

Computed on insert in the Python backend before the INSERT. Unique constraint at DB level: `UNIQUE(workspace_id, normalized_alias) WHERE deleted_at IS NULL` (partial unique index).

If a conflict is detected, the API returns 409 with the existing alias details so the frontend can show which canonical term already owns that alias.

---

## 4. Risks + Rollback Notes

| Risk | Mitigation |
|------|-----------|
| Fuzzy matching quality | Start with simple Levenshtein + keyword scoring; no ML. Candidates list lets users pick overrides. |
| Large glossary scan time | Synchronous is fine for <5000 terms. Add `completed_at` timing for monitoring. |
| Alias collision across workspaces | Workspace-scoped uniqueness (not global). Different workspaces can have the same alias mapping differently. |
| Migration rollback | All 4 tables are new (no ALTER). Rollback = `DROP TABLE IF EXISTS` in reverse order. No existing data affected. |
| Frontend tab clutter | Sync Suggestions tab only visible when a document is selected and glossary_terms exist. |

---

## 5. Task IDs

| ID | File(s) | Description |
|----|---------|-------------|
| SUGGEST-01 | `server/migrations/008_suggested_fields.sql` | Create 4 tables + indexes |
| SUGGEST-02 | `server/ulid.py` | Add prefixes: `sgr_`, `sug_`, `glt_`, `gla_` |
| SUGGEST-03 | `server/routes/suggestions.py` | Suggestion runs + suggestions endpoints |
| SUGGEST-04 | `server/routes/glossary.py` | Glossary terms + aliases endpoints |
| SUGGEST-05 | `server/suggestion_engine.py` | Heuristic suggestion generator + fuzzy matching |
| SUGGEST-06 | `server/pdf_proxy.py` | Register new routers |
| SUGGEST-07 | `ui/viewer/index.html` | Sync Suggestions tab + grouped rendering + Accept/Reject UI |
| SUGGEST-08 | `docs/handoff/V251_SUGGESTED_FIELDS_AUDIT.md` | Phase 4 verification report |

---

*Created: February 2026 — Orchestrate OS v2.51*
