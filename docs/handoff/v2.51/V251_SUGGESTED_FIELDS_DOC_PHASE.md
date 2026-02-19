# v2.51 Suggested Fields + Alias Builder (Sync Mode) — DOC Phase

> DOC phase only — no implementation, no migrations, no route changes.
> Read/audit only, then document.

---

## Repo Audit Snapshot

### Glossary Tables — Confirmed Present

Both tables exist in the live database schema (created by migration `008_suggested_fields.sql`):

| Table | PK Prefix | Columns | Unique Constraints | Foreign Keys |
|-------|-----------|---------|-------------------|--------------|
| `glossary_terms` | `glt_` | 13 (id, workspace_id, field_key, display_name, description, data_type, category, is_required, created_at, updated_at, deleted_at, version, metadata) | `(workspace_id, field_key) WHERE deleted_at IS NULL` | workspaces |
| `glossary_aliases` | `gla_` | 10 (id, workspace_id, term_id, alias, normalized_alias, source, created_by, created_at, deleted_at, metadata) | `(workspace_id, normalized_alias) WHERE deleted_at IS NULL` | workspaces, glossary_terms, users |

**Source check**: `CHECK (source = ANY (ARRAY['manual', 'suggestion', 'import']))` enforced at DB level.

### Suggestion Infrastructure — Confirmed Present

Both tables exist in the live database schema:

| Table | PK Prefix | Columns | Check Constraints | Foreign Keys |
|-------|-----------|---------|-------------------|--------------|
| `suggestion_runs` | `sgr_` | 9 (id, workspace_id, document_id, status, total_suggestions, created_at, completed_at, created_by, metadata) | `status IN ('running', 'completed', 'failed')` | workspaces, documents, users |
| `suggestions` | `sug_` | 15 (id, workspace_id, run_id, document_id, source_field, suggested_term_id, match_score, match_method, status, resolved_by, resolved_at, candidates, created_at, version, metadata) | `match_method IN ('exact', 'fuzzy', 'keyword', 'none')`, `status IN ('pending', 'accepted', 'rejected', 'dismissed')` | workspaces, suggestion_runs, documents, glossary_terms, users |

**Index count**: 11 secondary indexes across all 4 tables (workspace, document, run, status).

### Route Files — Confirmed Present

| File | Endpoints | Auth |
|------|-----------|------|
| `server/routes/suggestions.py` | POST `/documents/{id}/suggestion-runs`, GET `/documents/{id}/suggestions`, PATCH `/suggestions/{id}` | EITHER (GET/POST runs), BEARER (PATCH) |
| `server/routes/glossary.py` | GET `/glossary/terms`, POST `/glossary/terms`, POST `/glossary/aliases` | EITHER (GET), BEARER (POST) |

### Suggestion Engine — Confirmed Present

`server/suggestion_engine.py` implements three matching strategies:

| Strategy | Threshold | Scoring |
|----------|-----------|---------|
| Exact | 1.0 | Direct normalized string match OR existing alias lookup |
| Fuzzy | ≥ 0.6 | Levenshtein ratio via `SequenceMatcher` |
| Keyword | ≥ 0.2 | Category-based keyword overlap (4 categories: financial, identity, contract, catalog) |

Engine normalizes field names by: stripping `__c` suffix, expanding camelCase, replacing `_`/`-` with spaces, collapsing whitespace, lowercasing. Alias lookup is checked first (short-circuits to exact if match found). Candidates are sorted by score descending, top 3 returned per source field.

### Frontend Sync Tab — Confirmed Present

The UI (`ui/viewer/index.html`) has a Sync Suggestions panel with:
- CSS: `#sync-suggestions-panel`, `.sync-run-btn`, `.sync-group`, `.sync-row`, `.sync-accept-btn`, `.sync-reject-btn`
- JS functions: `_syncTogglePanel()`, `_syncRunSuggestions()`, `_syncFetchSuggestions()`, `_syncRenderSuggestions()`, `_syncRenderDemoSuggestions()`, `_syncAccept()`, `_syncReject()`, `_syncUpdateStatus()`
- Demo fallback: When no document ID is available, renders sample suggestions for sandbox/demo use
- Grouped rendering: Suggestions grouped by match method (exact/fuzzy/keyword/unmatched)

### Reusable Patterns Identified

| Pattern | Source Location | Reuse in Suggested Fields |
|---------|----------------|--------------------------|
| **Triage items status lifecycle** | `triage_items` table: open → in_review → resolved → dismissed | `suggestions` table: pending → accepted → rejected → dismissed |
| **Triage registry UX** | Lane cards (Pre-Flight, Semantic, Patch Review), nested parent/child table, Accept/Reject buttons | Sync Suggestions as 4th lane; grouped by match type; Accept/Reject per suggestion |
| **Audit emission** | `server/audit.py: emit_audit_event(cur, workspace_id, event_type, actor_id, ...)` — used in 16+ route files | All mutations emit: `suggestion_run.created`, `suggestion.accepted`, `suggestion.rejected`, `glossary_alias.created`, `glossary_term.created` |
| **Optimistic concurrency** | `version` column on `triage_items`, `patches`, `documents`, `glossary_terms` | `suggestions.version` — PATCH requires version match, 409 STALE_VERSION on conflict |
| **Workspace context** | `_require_workspace_id()` in `glossary.py` — explicit `X-Workspace-Id` header or body `workspace_id` required, membership verified against `user_workspace_roles` | Applied to all 3 glossary endpoints; 422 MISSING_WORKSPACE if absent, 403 FORBIDDEN if non-member |
| **Document-scoped access** | `_verify_workspace_access()` in `suggestions.py` — fetch document, get its workspace_id, verify user has role there | Applied to all 3 suggestion endpoints (runs, list, patch) |
| **Soft delete** | `deleted_at IS NULL` filter on all reads; unique constraints use partial index with `WHERE deleted_at IS NULL` | Applied to glossary_terms, glossary_aliases |
| **ULID generation** | `server/ulid.py: generate_id(prefix)` | Prefixes registered: `glt_`, `gla_`, `sgr_`, `sug_` |
| **API envelope** | `server/api_v25.py: envelope()`, `collection_envelope()`, `error_envelope()` | All endpoints return `{data, meta}` or `{error, meta}` with `request_id` and `timestamp` |

---

## Proposed Implementation (Additive)

> All items below are already implemented. This section documents the contracts as-built for reference.

### API Contracts

#### POST `/api/v2.5/documents/{document_id}/suggestion-runs`

Triggers a synchronous suggestion run against one document.

```
Auth: EITHER (Bearer or API Key)
Access: Document-scoped — user must have role in document's workspace

Request: {} (empty body)
Response 201:
{
  "data": {
    "id": "sgr_...",
    "workspace_id": "ws_...",
    "document_id": "doc_...",
    "status": "completed",
    "total_suggestions": 4,
    "created_at": "2026-02-14T17:00:00+00:00",
    "completed_at": "2026-02-14T17:00:01+00:00",
    "created_by": "usr_...",
    "metadata": {}
  },
  "meta": { "request_id": "req_...", "timestamp": "..." }
}

Error 404: Document not found or user lacks workspace access
Error 500: Suggestion engine failure (SUGGESTION_ENGINE_FAILED)
```

**Audit event**: `suggestion_run.created` with `{document_id, total_suggestions}`.

#### GET `/api/v2.5/documents/{document_id}/suggestions`

Lists suggestions for a document with optional status filter and cursor pagination.

```
Auth: EITHER
Access: Document-scoped

Query params: ?status=pending&cursor=sug_...&limit=50
Response 200:
{
  "data": [
    {
      "id": "sug_...",
      "workspace_id": "ws_...",
      "run_id": "sgr_...",
      "document_id": "doc_...",
      "source_field": "Pmt_Freq",
      "suggested_term_id": "glt_...",
      "match_score": 0.85,
      "match_method": "fuzzy",
      "status": "pending",
      "resolved_by": null,
      "resolved_at": null,
      "candidates": [
        {"term_id": "glt_A", "score": 0.85, "method": "fuzzy"},
        {"term_id": "glt_B", "score": 0.62, "method": "fuzzy"}
      ],
      "created_at": "...",
      "version": 1,
      "metadata": {}
    }
  ],
  "meta": {
    "request_id": "req_...",
    "timestamp": "...",
    "pagination": { "cursor": null, "has_more": false, "limit": 50 }
  }
}
```

#### PATCH `/api/v2.5/suggestions/{suggestion_id}`

Accept, reject, or dismiss a suggestion. Requires optimistic concurrency version.

```
Auth: BEARER only
Access: Suggestion-scoped (user must have role in suggestion's workspace)

Request: { "status": "accepted", "version": 1 }
  — or: { "status": "accepted", "version": 1, "selected_term_id": "glt_..." }
  — or: { "status": "rejected", "version": 1 }
  — or: { "status": "dismissed", "version": 1 }

Response 200:
{
  "data": {
    "id": "sug_...",
    "status": "accepted",
    "resolved_by": "usr_...",
    "resolved_at": "2026-02-14T17:05:00+00:00",
    "version": 2,
    "alias_id": "gla_..."  // only present on accept
  },
  "meta": { "request_id": "req_...", "timestamp": "..." }
}

Error 400: INVALID_STATE — suggestion already resolved (not pending)
Error 400: VALIDATION_ERROR — invalid status or missing version
Error 404: Suggestion not found or user lacks workspace access
Error 409: STALE_VERSION — version mismatch (concurrent modification)
```

**Accept side-effect**: Creates a `glossary_aliases` row (source = 'suggestion') linking source_field → term. If alias already exists, reuses existing alias_id.

**Audit events**: `suggestion.accepted` or `suggestion.rejected` with `{source_field, term_id, alias_id}`. On new alias creation: `glossary_alias.created`.

#### GET `/api/v2.5/glossary/terms`

Lists canonical glossary terms with search, category filter, and cursor pagination.

```
Auth: EITHER
Workspace: REQUIRED — via X-Workspace-Id header or JWT workspace_id claim
  Missing → 422 MISSING_WORKSPACE
  Non-member → 403 FORBIDDEN

Query params: ?query=payment&category=financial&cursor=glt_...&limit=50
Response 200:
{
  "data": [
    {
      "id": "glt_...",
      "workspace_id": "ws_...",
      "field_key": "Payment_Frequency__c",
      "display_name": "Payment Frequency",
      "description": null,
      "data_type": "string",
      "category": "financial",
      "is_required": false,
      "created_at": "...",
      "updated_at": "...",
      "deleted_at": null,
      "version": 1,
      "metadata": {}
    }
  ],
  "meta": { "pagination": {...}, ... }
}
```

Search (`query` param) applies `ILIKE` across `field_key`, `display_name`, and `description`.

#### POST `/api/v2.5/glossary/terms`

Creates a new canonical glossary term.

```
Auth: BEARER only
Workspace: REQUIRED — via X-Workspace-Id header, body workspace_id, or JWT claim

Request: {
  "field_key": "Payment_Frequency__c",
  "display_name": "Payment Frequency",
  "description": "How often royalty payments are issued",
  "data_type": "string",
  "category": "financial",
  "is_required": false,
  "metadata": {}
}

Response 201: { "data": { "id": "glt_...", ... }, "meta": {...} }
Error 409: DUPLICATE — field_key already exists in workspace
Error 422: MISSING_WORKSPACE
Error 403: FORBIDDEN
```

**Audit event**: `glossary_term.created` with `{field_key, display_name}`.

#### POST `/api/v2.5/glossary/aliases`

Creates a manual alias mapping from a source field name to a canonical term.

```
Auth: BEARER only
Workspace: REQUIRED — via X-Workspace-Id header, body workspace_id, or JWT claim

Request: { "term_id": "glt_...", "alias": "Pmt Freq" }

Response 201: {
  "data": {
    "id": "gla_...",
    "workspace_id": "ws_...",
    "term_id": "glt_...",
    "alias": "Pmt Freq",
    "normalized_alias": "pmt freq",
    "source": "manual",
    "created_by": "usr_...",
    "created_at": "...",
    "deleted_at": null,
    "metadata": {}
  },
  "meta": {...}
}

Error 404: NOT_FOUND — term not found in workspace
Error 409: DUPLICATE_ALIAS — normalized_alias already exists in workspace
  details: { "existing_alias_id", "existing_term_id", "existing_field_key" }
Error 422: MISSING_WORKSPACE
Error 403: FORBIDDEN
```

**Alias normalization**: `LOWER(TRIM(COLLAPSE_WHITESPACE(alias)))`. Computed in Python before INSERT. Uniqueness enforced by partial unique index at DB level.

**Audit event**: `glossary_alias.created` with `{term_id, alias, normalized_alias}`.

### DB Plan (As-Built)

All 4 tables created by migration `008_suggested_fields.sql`. No ALTER on existing tables. All additive.

| Table | Rows at Deploy | Index Count | FK Count | Audit Linkage |
|-------|----------------|-------------|----------|---------------|
| `glossary_terms` | 0 (needs seeding) | 3 (PK + field_key unique + workspace) | 1 (workspaces) | `glossary_term.created` |
| `glossary_aliases` | 0 | 4 (PK + normalized unique + term + workspace) | 3 (workspaces, terms, users) | `glossary_alias.created` |
| `suggestion_runs` | 0 | 3 (PK + document + workspace) | 3 (workspaces, documents, users) | `suggestion_run.created` |
| `suggestions` | 0 | 5 (PK + document + run + status + workspace) | 5 (workspaces, runs, documents, terms, users) | `suggestion.accepted/rejected` |

**Rollback**: `DROP TABLE suggestions, suggestion_runs, glossary_aliases, glossary_terms CASCADE;`

### FE Plan (As-Built)

**Sync Suggestions tab** in grid float controls (`ui/viewer/index.html`):

| Component | Implementation | Notes |
|-----------|---------------|-------|
| Toggle button | "Sync" button in grid header float controls | Toggles `#sync-suggestions-panel` visibility |
| Run Suggestions | `_syncRunSuggestions()` | POST to `/documents/{id}/suggestion-runs`, then fetches results |
| Grouped list | `_syncRenderSuggestions()` | Groups by `match_method`: exact → fuzzy → keyword → unmatched |
| Per-suggestion row | Source field, match score badge, best match term, Accept/Reject buttons | Pending = yellow, accepted = green, rejected = red |
| Accept flow | `_syncAccept(id, version)` → PATCH with `{status: "accepted", version}` | Auto-creates alias; re-renders list |
| Reject flow | `_syncReject(id, version)` → PATCH with `{status: "rejected", version}` | Re-renders list |
| Demo fallback | `_syncRenderDemoSuggestions()` | When no document ID available (sandbox/demo mode) |

**Admin Glossary Builder**: Not yet implemented as a dedicated UI. Terms can be created via:
1. POST `/api/v2.5/glossary/terms` (API)
2. Seed script / migration (bulk insert)
3. Aliases auto-created via suggestion Accept flow

### Heuristics v1 Plan (As-Built)

`server/suggestion_engine.py` implements a 3-tier matching pipeline:

```
For each source_field in document.metadata.column_headers:
  1. Normalize: strip __c, expand camelCase, replace _/- with space, lowercase
  2. Alias lookup: check glossary_aliases for exact normalized match → score 1.0
  3. If no alias match, compare against all glossary_terms:
     a. Exact: normalized source == normalized term → score 1.0
     b. Fuzzy: SequenceMatcher ratio ≥ 0.6 → score = ratio
     c. Keyword: category-based keyword overlap ≥ 0.2 → score = (matched_keywords * 0.1) + (word_overlap * 0.15), capped at 0.6
  4. Sort candidates by score descending, take top 3
  5. Best candidate becomes suggested_term_id; all top 3 stored in candidates JSONB
  6. If no candidates found: match_method = "none", score = 0.0
```

**Keyword categories** (4 domains with 10-15 terms each):
- `financial`: payment, revenue, royalty, rate, amount, fee, cost, price, billing, invoice, currency, term, frequency
- `identity`: account, name, contact, email, phone, address, city, state, country, zip, postal
- `contract`: contract, agreement, effective, expiration, start, end, status, type, category, opportunity, deal
- `catalog`: title, artist, album, track, isrc, upc, label, genre, release, catalog, territory, rights

---

## Priority Task Plan (P0–P4)

> All SUGGEST-01 through SUGGEST-08 are implemented. This plan reflects the current state and remaining work.

### P0 — Complete (Ship-blocking, done)

| ID | Description | Status | Acceptance Criteria |
|----|-------------|--------|-------------------|
| SUGGEST-01 | Migration 008: 4 tables + 11 indexes + constraints | DONE | All 4 tables exist, constraints enforced, rollback is DROP CASCADE |
| SUGGEST-02 | ULID prefixes: glt_, gla_, sgr_, sug_ | DONE | `generate_id()` produces correct prefixes |
| SUGGEST-03 | Suggestion runs + suggestions endpoints | DONE | POST creates run, GET lists with pagination, PATCH with OCC |
| SUGGEST-04 | Glossary terms + aliases endpoints | DONE | GET/POST terms, POST aliases, 409 on duplicate, workspace-scoped |
| SUGGEST-05 | Suggestion engine: exact + fuzzy + keyword | DONE | Top 3 candidates, alias shortcut, normalized matching |
| SUGGEST-06 | Router registration in pdf_proxy.py | DONE | Both routers mounted, health check passes |

### P1 — Complete (Functional, done)

| ID | Description | Status | Acceptance Criteria |
|----|-------------|--------|-------------------|
| SUGGEST-07 | Frontend Sync tab: panel, grouped rendering, Accept/Reject | DONE | Toggle, run, render, accept, reject, demo fallback all functional |
| SUGGEST-08 | Audit + verification report | DONE | 71/71 checks pass including multi-workspace routing |

### P2 — Recommended Before Merge

| ID | Description | Status | Dependency | Acceptance Criteria |
|----|-------------|--------|------------|-------------------|
| SUGGEST-09 | Update API docs to require X-Workspace-Id for glossary endpoints | TODO | None | All glossary curl examples show X-Workspace-Id header |
| SUGGEST-10 | Changelog note: glossary calls without workspace → 422 | TODO | SUGGEST-09 | Breaking change documented in CHANGELOG.md |
| SUGGEST-11 | Frontend: pass workspace_id explicitly on glossary read/write | TODO | SUGGEST-09 | Frontend clients send X-Workspace-Id on every glossary call |
| SUGGEST-12 | Glossary term seeding script | TODO | None | Script imports from field_meta.json or canonical schema; produces glossary_terms rows |
| SUGGEST-13 | Document column_headers population during XLSX import | TODO | None | Import pipeline stores `metadata.column_headers` on documents rows |

### P3 — Enhancement

| ID | Description | Status | Dependency | Acceptance Criteria |
|----|-------------|--------|------------|-------------------|
| SUGGEST-14 | Glossary picker in Accept flow (override suggested term) | TODO | SUGGEST-12 | Frontend shows searchable glossary dropdown when accepting |
| SUGGEST-15 | Batch-level suggestion runs (all docs in a batch) | TODO | SUGGEST-13 | POST `/batches/{id}/suggestion-runs` runs engine across all docs |
| SUGGEST-16 | Backfill script for existing documents without column_headers | TODO | SUGGEST-13 | Script parses stored XLSX/CSV and populates metadata.column_headers |
| SUGGEST-17 | Suggestion deduplication across runs | TODO | None | Upsert keyed on `(document_id, source_field)` prevents duplicate suggestions |

### P4 — Future / Low Priority

| ID | Description | Status | Dependency | Acceptance Criteria |
|----|-------------|--------|------------|-------------------|
| SUGGEST-18 | Admin Glossary Builder UI (term CRUD, alias management) | TODO | SUGGEST-12 | Dedicated admin panel for managing glossary terms and aliases |
| SUGGEST-19 | Suggestion analytics (acceptance rate, top unmatched fields) | TODO | SUGGEST-15 | Dashboard widget showing suggestion resolution metrics |
| SUGGEST-20 | ML-based matching (embeddings, learned aliases) | TODO | SUGGEST-17 | Replace or augment heuristic engine with vector similarity |

---

## Clarity Questions

1. **Glossary term seeding source**: Should the initial glossary terms be imported from the existing `field_meta.json` client-side cache, or from the canonical schema bundle? Both are available — which is the authoritative source for field definitions?

2. **Column headers extraction timing**: Should `metadata.column_headers` be populated at XLSX import time (during the existing upload/parse pipeline) or as a separate backfill step? Import-time is cleaner but requires modifying the import pipeline; backfill is non-invasive but creates a gap for new documents until the pipeline is updated.

3. **Frontend workspace context source**: When the frontend calls glossary endpoints, should it read the workspace_id from the JWT claims, from a UI context variable (e.g., `currentWorkspaceId`), or from a dedicated workspace selector component? This determines how SUGGEST-11 is implemented.

4. **Suggestion deduplication policy**: When a user re-runs suggestions on the same document, should the system (a) create a fresh set of suggestions alongside old ones, (b) upsert and overwrite previous pending suggestions, or (c) skip source fields that already have resolved (accepted/rejected) suggestions?

5. **Alias edit/delete support**: The current alias endpoint only supports creation. Should alias deletion (soft delete via `deleted_at`) or alias reassignment (move alias to a different term) be supported before merge, or deferred to P4?

---

## Go/No-Go

**GO** — Clear to proceed to Clarity response stage.

**Rationale**:
- All 8 core tasks (SUGGEST-01 through SUGGEST-08) are implemented and verified (71/71 checks pass)
- Database schema is stable (4 tables, 11 indexes, all constraints enforced)
- Multi-workspace routing is explicit and enforced (no LIMIT 1 fallback)
- API contracts follow established `/api/v2.5` envelope pattern
- Frontend Sync tab is functional with demo fallback
- Audit coverage on all mutations
- No blockers — all clarity questions are enhancement-scoping decisions, not implementation blockers

**Pre-merge items** (P2) are documentation and data-seeding tasks that don't block the feature from functioning correctly in its current state.

---

*Audited: February 2026 — Orchestrate OS v2.51*
*Verification baseline: 71 checks (scripts/verify_suggested_fields.py)*
