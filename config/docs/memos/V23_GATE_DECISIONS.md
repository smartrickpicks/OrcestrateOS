# V2.3 Gate Decisions (Locked)

This memo captures the locked gate rules enforced by V2.3. Each gate has a deterministic console log (`[V2.3-GATE][G#] PASS|FAIL <metric>`) emitted at runtime.

## G1 — Contract ID Derivation Priority

**Rule:** Contract IDs are derived using a strict priority chain:
1. Extracted path ID from canonical URL (`source=extracted`)
2. Hash of canonical URL (`source=url_hash`)
3. Fallback signature from file_name/contract_key (`source=fallback_sig`)

**Locked behavior:**
- `deriveContractId(row, true)` returns `{ contract_id, contract_id_source }`.
- URL canonicalization: trim, strip trailing slashes, remove query/hash, decodeURIComponent, lowercase.
- Header-like values (matching known header strings) are rejected at each stage.
- `contract_id_source` is persisted per contract in the index.

**Cross-ref:** `docs/decisions/DECISION_ID_EXTRACTION.md`, `config/id_extraction_rules.json`

## G2 — ContractIndex Rebuild Policy

**Rule:** ContractIndex is always rebuilt from the live workbook (never from cached/serialized index) on every load path.

**Covered paths (4):**
1. Upload — after signals and seed, before final render
2. Session-load — after session restore populates workbook
3. Restore — after workbook restoration from IndexedDB
4. Demo/sandbox — after dataset population and signal generation

**Locked behavior:**
- Session restore is seed-only; never final authority for the index.
- On build failure: fail-open banner, `_failOpen = true`, index degraded gracefully.
- `stagedLoader.setStage('indexing')` shown during rebuild on restore/session paths.

**Cross-ref:** `docs/decisions/DECISION_HIERARCHY.md`

## G3 — Unknown Column Thresholds

**Rule:** Thresholds are constants, not configurable at runtime:
- `_UNKNOWN_WARN_THRESHOLD = 0` — any non-empty count > 0 triggers `severity: 'warning'`
- `_UNKNOWN_BLOCKER_THRESHOLD = 3` — non-empty count > 3 triggers `severity: 'blocker'`

**Locked behavior:**
- `_routeUnknownColumns` computes severity per column: `col.count_nonempty > 3 ? 'blocker' : 'warning'`.
- Pre-flight triage items use computed severity from the rollup (`uc.severity`), not hardcoded.
- Columns with `count_nonempty === 0` are skipped entirely.

**Cross-ref:** `docs/decisions/DECISION_UNKNOWN_COLUMNS.md`

## G4 — Unknown Column Attachment (Frequency Vote)

**Rule:** Unknown columns are attached to contracts via contract-section-scoped frequency vote:
- For each unknown column's contract section, count contract ID votes across all rows.
- Attach to top contract if `top_share >= 60%` OR `top_count >= 2 * second_count`.
- Otherwise, attach to batch-level.

**Locked behavior:**
- `attach_confidence` = `Math.round(topShare * 100)`.
- Deduplication by `batch_id|level|attachTo|sheet|normalized_name`.
- Each routed entry emits `UNKNOWN_COLUMN_DETECTED` audit event.

**Cross-ref:** `docs/decisions/DECISION_UNKNOWN_COLUMNS.md`

## G5 — Header-Echo Sanitization

**Rule:** Parse-time row removal when canonical header-token overlap >= 60% of populated columns.

**Locked behavior:**
- Applied to both CSV and XLSX parse paths.
- Match ratio = `matchCount / totalFields` where `totalFields` = number of non-empty cells.
- Removed rows are not included in the workbook.
- Audit event: `ROW_SANITIZED_HEADER_ECHO` with `metadata: { sheet_name, row_index, match_ratio }`.

## G6 — Storage Policy (localStorage vs IndexedDB)

**Rule:** localStorage is reserved for preferences and pointers only. Workbook/dataset blobs are stored exclusively in IndexedDB via SessionDB.

**Locked behavior:**
- Zero `localStorage.setItem` / `localStorage.getItem` calls for `STORAGE_KEY_DATASET`.
- `saveWorkbookToCache()` writes to IndexedDB only.
- `activateDataset()` reads from upload library metadata + in-memory `allData` fallback.
- `isPicklistValidationEnabled()` checks `allData` root + summary + upload library (no blob reads).
- `resetDemoState()` still calls `localStorage.removeItem(STORAGE_KEY_DATASET)` for cleanup of legacy data.

**Cross-ref:** `docs/decisions/DECISION_STORAGE_POLICY.md`

## G7 — Contract Selector Semantics

**Rule:** Primary contract selector count and options are dataset-wide across all contract sections.

**Locked behavior:**
- Stat badge shows `datasetWideCount` from `ContractIndex.listContracts()`.
- Dropdown always lists all contracts; contract section context shown as secondary `[N in section]` annotation.
- Primary count does not change when contract section filter changes.

## G8 — Missing URL / Orphan Handling

**Rule:** Rows with no valid `file_url` and no valid `file_name`/`contract_key` are orphaned to batch-level.

**Locked behavior:**
- Orphan rows pushed to `index.orphan_rows` with `reason: 'missing_url_and_name'`.
- Orphan rows are counted in `index.stats.orphan_rows` but not indexed under any contract.
- No contract is created for orphan rows.

## G9 — Unknown Column Payload Completeness

**Rule:** Every `UNKNOWN_COLUMN_DETECTED` audit event must include the full payload:
- `batch_id`, `sheet`, `contract_id` (or null), `contract_id_source` (or null), `attach_confidence`
- Plus: `column`, `normalized`, `non_empty`, `severity`, `level`

**Locked behavior:**
- Payload assembled in `_routeUnknownColumns` after frequency vote resolution.
- `contract_id_source` pulled from `index.contracts[contractId].contract_id_source`.
