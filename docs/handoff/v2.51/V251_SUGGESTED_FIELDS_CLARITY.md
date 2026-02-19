# v2.51 Suggested Fields + Alias Builder — Clarity Alignment

> CLARITY phase only — no code edits.
> Input: `docs/handoff/V251_SUGGESTED_FIELDS_DOC_PHASE.md` + authoritative decision answers.

---

## 1. Alignment Result

**ALIGNED**

All 5 clarity questions have authoritative answers. No conflicts with existing implementation. One naming correction requires implementation work (rename "Sync" → "Suggestions" in product language). One new scope addition (alias edit support) expands the task list.

---

## 2. Decision Alignment Detail

### Q1: Glossary Term Seeding Source

**Decision**: Governance JSON (`field_meta`) is the source of truth. DB seeding is idempotent and additive from that source. Aliases are part of governed schema evolution.

**Alignment**: ALIGNED. The existing `POST /glossary/terms` endpoint supports idempotent creation (409 on duplicate `field_key` per workspace). The seeding script (SUGGEST-12) will read from `field_meta.json` and POST each term. No schema change needed — the `source` column on `glossary_aliases` already supports `'import'` as a value for governance-driven alias creation.

**Delta from DOC plan**: None. SUGGEST-12 task description updated to reference governance JSON explicitly.

### Q2: Suggestion Input Timing

**Decision**: Suggestions run after OCR/text extraction completes. Primary source is extracted labels/text. If `column_headers` is missing, use safe fallback extraction paths — do not block the run.

**Alignment**: ALIGNED with one delta. The current engine (`suggestion_engine.py`) returns an empty list and logs a warning when `column_headers` is missing. The decision says "do not block run" — the current behavior already does not block (returns 201 with `total_suggestions: 0`), but the engine could attempt fallback extraction from other metadata fields. This is a minor enhancement, not a blocker.

**Delta from DOC plan**: New task SUGGEST-21 added (P3) — fallback extraction paths when `column_headers` is absent. The engine should attempt to extract field labels from `metadata.section_headers`, `metadata.sheet_names`, or document `file_name` patterns before returning zero suggestions.

### Q3: Workspace Routing

**Decision**: Frontend must always send explicit workspace context for glossary calls. Keep `X-Workspace-Id` contract. Suggestions UX follows current v2.5 envelope and auth patterns.

**Alignment**: ALIGNED. This is exactly what was implemented in the multi-workspace glossary routing fix. `_require_workspace_id()` enforces `X-Workspace-Id` header, body `workspace_id`, or JWT claim. 422 MISSING_WORKSPACE if absent. Suggestion endpoints use document-scoped access (no workspace header needed — workspace derived from document's `workspace_id`).

**Delta from DOC plan**: None. SUGGEST-11 (frontend passes workspace explicitly) confirmed as required.

### Q4: Dedup Policy

**Decision**: Alias normalization required. Same normalized alias + same term = idempotent (return existing). Same normalized alias + different term = conflict (409). Keep behavior auditable.

**Alignment**: ALIGNED. This is exactly the current behavior:
- `normalized_alias` computed via `LOWER(TRIM(COLLAPSE_WHITESPACE(alias)))` before INSERT.
- DB unique constraint: `(workspace_id, normalized_alias) WHERE deleted_at IS NULL`.
- On conflict: 409 DUPLICATE_ALIAS with `{existing_alias_id, existing_term_id, existing_field_key}`.
- All alias creation emits `glossary_alias.created` audit event.

The question in DOC was about suggestion dedup (re-running suggestions on same document), not alias dedup. Clarification: the decision covers alias dedup policy (which is already correct). Suggestion re-run dedup (SUGGEST-17) remains a P3 enhancement — current behavior creates fresh suggestions alongside old ones, which is acceptable since old suggestions retain their resolved state for audit trail.

**Delta from DOC plan**: None. SUGGEST-17 stays at P3 with the clarification that it's about suggestion-level dedup, not alias-level.

### Q5: Alias Edit Support

**Decision**: Include alias edit support in scope (versioned update + audit event). UI must allow alias update from admin glossary management surface.

**Alignment**: NEW SCOPE. The current implementation only supports alias creation. This decision adds:
- PATCH `/api/v2.5/glossary/aliases/{alias_id}` — update `term_id` (reassign) or `alias` text (rename), with `version` for optimistic concurrency.
- `glossary_aliases` table needs a `version` column (currently absent) and `updated_at` timestamp.
- Audit event: `glossary_alias.updated` with `{before_term_id, after_term_id, before_alias, after_alias}`.
- Admin Glossary Builder UI (SUGGEST-18) promoted from P4 to P2 for alias edit surface.

**Delta from DOC plan**:
- New task SUGGEST-22 (P2): Add `version` + `updated_at` columns to `glossary_aliases` (migration 009).
- New task SUGGEST-23 (P2): PATCH `/glossary/aliases/{id}` endpoint with OCC + audit.
- SUGGEST-18 promoted from P4 → P2 (admin UI needed for alias edit).

### Naming Correction: "Sync" → "Suggestions"

**Decision**: Stop calling it "Sync tab" in product language. Preferred: "Suggestions" or "Field Suggestions". Context: suggested contract line-item/field mappings. Action language: Accept / Decline / Dismiss.

**Alignment**: Requires implementation changes. Current codebase uses "Sync" throughout:
- CSS: `#sync-suggestions-panel`, `.sync-run-btn`, `.sync-group`, `.sync-row`
- JS: `_syncTogglePanel()`, `_syncRunSuggestions()`, `_syncRenderSuggestions()`, `_syncAccept()`, `_syncReject()`
- Button label: "Sync" in grid float controls

**Delta from DOC plan**: New task SUGGEST-24 (P2) — rename all "Sync" references to "Suggestions" in frontend code and labels. CSS class names can stay as internal identifiers (no user-facing impact), but button labels, panel headers, and user-visible text must change. "Reject" → "Decline" in button labels per naming decision.

---

## 3. Updated Task List (P0–P4)

### P0 — Complete (Ship-blocking, done)

| ID | Description | Status |
|----|-------------|--------|
| SUGGEST-01 | Migration 008: 4 tables + 11 indexes + constraints | DONE |
| SUGGEST-02 | ULID prefixes: glt_, gla_, sgr_, sug_ | DONE |
| SUGGEST-03 | Suggestion runs + suggestions endpoints | DONE |
| SUGGEST-04 | Glossary terms + aliases endpoints | DONE |
| SUGGEST-05 | Suggestion engine: exact + fuzzy + keyword | DONE |
| SUGGEST-06 | Router registration in pdf_proxy.py | DONE |

### P1 — Complete (Functional, done)

| ID | Description | Status |
|----|-------------|--------|
| SUGGEST-07 | Frontend Suggestions panel: grouped rendering, Accept/Decline/Dismiss | DONE |
| SUGGEST-08 | Audit + verification report (71/71 checks) | DONE |

### P2 — Required Before Merge

| ID | Description | Status | Dependency | Acceptance Criteria |
|----|-------------|--------|------------|-------------------|
| SUGGEST-09 | Update API docs: require X-Workspace-Id for glossary endpoints | TODO | None | All glossary curl examples show X-Workspace-Id header |
| SUGGEST-10 | Changelog: glossary calls without workspace → 422 | TODO | SUGGEST-09 | Breaking change documented |
| SUGGEST-11 | Frontend: pass workspace_id explicitly on glossary read/write | TODO | SUGGEST-09 | Frontend sends X-Workspace-Id on every glossary call |
| SUGGEST-12 | Glossary term seeding from governance JSON (`field_meta`) | TODO | None | Idempotent script reads `field_meta.json`, POSTs terms; re-runnable |
| SUGGEST-13 | Document `column_headers` population during import | TODO | None | Import pipeline stores `metadata.column_headers` on documents rows |
| SUGGEST-22 | Migration 009: add `version` + `updated_at` to `glossary_aliases` | TODO | None | Column exists, defaults to 1/now(), no data loss |
| SUGGEST-23 | PATCH `/glossary/aliases/{id}` endpoint (OCC + audit) | TODO | SUGGEST-22 | Versioned update, `glossary_alias.updated` audit event, workspace-scoped |
| SUGGEST-18 | Admin Glossary Builder UI (term list, alias edit surface) | TODO | SUGGEST-23 | Admin can view terms, edit/reassign aliases, delete aliases |
| SUGGEST-24 | Rename "Sync" → "Suggestions" in all frontend labels and headers | TODO | None | Button says "Suggestions", panel header says "Field Suggestions", action buttons say Accept/Decline/Dismiss |

### P3 — Enhancement

| ID | Description | Status | Dependency | Acceptance Criteria |
|----|-------------|--------|------------|-------------------|
| SUGGEST-14 | Glossary picker in Accept flow (override suggested term) | TODO | SUGGEST-12 | Searchable dropdown when accepting a suggestion |
| SUGGEST-15 | Batch-level suggestion runs | TODO | SUGGEST-13 | POST `/batches/{id}/suggestion-runs` across all docs |
| SUGGEST-16 | Backfill script for existing documents without `column_headers` | TODO | SUGGEST-13 | Script parses stored XLSX/CSV, populates metadata |
| SUGGEST-17 | Suggestion deduplication across runs | TODO | None | Upsert on `(document_id, source_field)` for pending suggestions |
| SUGGEST-21 | Fallback extraction paths when `column_headers` is absent | TODO | None | Engine tries `section_headers`, `sheet_names`, `file_name` patterns before returning zero |

### P4 — Future / Low Priority

| ID | Description | Status | Dependency | Acceptance Criteria |
|----|-------------|--------|------------|-------------------|
| SUGGEST-19 | Suggestion analytics (acceptance rate, top unmatched fields) | TODO | SUGGEST-15 | Dashboard widget with resolution metrics |
| SUGGEST-20 | ML-based matching (embeddings, learned aliases) | TODO | SUGGEST-17 | Vector similarity augments heuristic engine |

---

## 4. Remaining Non-Blocking Assumptions

1. **Governance JSON structure**: Assumed `field_meta.json` contains objects with at minimum `field_key`, `display_name`, `category`, and `data_type` fields. If the structure differs, SUGGEST-12 seeding script will need a mapping layer. This does not block implementation — the script can be adapted once the exact structure is confirmed.

2. **Alias edit scope**: Assumed alias edit means changing `term_id` (reassign to different canonical term) and/or `alias` text (rename), but not changing `workspace_id` (cross-workspace alias moves are not supported). Soft delete (`deleted_at`) already exists on the table.

3. **Frontend "Decline" vs "Reject"**: The decision says "Accept / Decline / Dismiss" for action language. Current backend uses `status: "rejected"` internally. Assumption: frontend button says "Decline" but the API value stays `"rejected"` — no backend rename needed. This is a presentation-layer-only change.

4. **Admin Glossary Builder access**: Assumed this UI surface is gated to `admin` and `architect` roles only (consistent with existing admin-only patterns like sandbox reset). Analyst and verifier roles can view suggestions and accept/decline but cannot directly edit glossary terms or aliases.

5. **Migration 009 scope**: Assumed `version` column on `glossary_aliases` defaults to `1` for existing rows and `updated_at` defaults to `created_at`. This is a safe additive migration with no data loss or constraint changes.

---

## 5. Go/No-Go for IMPLEMENT Phase

**GO** — Clear to proceed to implementation.

**Rationale**:
- All 5 clarity questions resolved with authoritative answers
- No conflicts with existing implementation
- New scope (alias edit, naming rename) is well-bounded and additive
- P2 task list is concrete with clear acceptance criteria and dependency ordering
- No blocking assumptions — all assumptions are resolvable during implementation without architectural changes
- Existing 71/71 verification baseline provides regression safety net

**Recommended implementation order**:
1. SUGGEST-24 (naming rename — quick, no backend changes)
2. SUGGEST-12 (glossary seeding — enables real suggestion runs)
3. SUGGEST-13 (column_headers population — enables real data flow)
4. SUGGEST-22 → SUGGEST-23 (alias versioning + edit endpoint — schema first, then route)
5. SUGGEST-18 (admin UI — depends on edit endpoint)
6. SUGGEST-09 → SUGGEST-10 → SUGGEST-11 (docs + frontend workspace context — can parallel with above)

---

*Clarity alignment completed: February 2026 — Orchestrate OS v2.51*
*Decision authority: User-provided clarity answers*
*Verification baseline: 71 checks (scripts/verify_suggested_fields.py)*
