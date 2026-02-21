# Audit Request: Pre-Flight Section Coverage, Schema Snapshot Gap, and Contract Count Drift

**Requested by:** Product Owner
**Date:** 2026-02-10
**Priority:** High
**Scope:** Pre-Flight pipeline, Schema Snapshot engine, Contract counting logic

---

## Summary

Three interrelated issues have been identified that affect the accuracy and completeness of the governance pipeline. This audit request covers:

1. **Pre-Flight contract section coverage** — Only "Accounts" appears in mojibake/OCR pre-flight items; other contract sections (Opportunities, Financials, Catalog, etc.) are missing.
2. **Schema Snapshot coverage gap** — The glossary contains 442 defined terms but only ~173 are matching against the workbook, yielding ~39% coverage instead of the expected 100%.
3. **Contract count drift** — Some views report 65 contracts while others report 64, indicating a counting inconsistency between subsystems.

---

## Issue 1: Pre-Flight Contract Section Coverage

### Observed Behavior
When the batch PDF scan runs, pre-flight items are created with only the "Accounts" contract section populated. Other sections such as Opportunities, Financials, Catalog, Schedule, V2 Add Ons, and Contacts do not appear even when the workbook contains data contract sections mapped to those sections.

### Root Cause Hypothesis
The function `_p1fExtractUniqueContracts()` (line ~18397) deduplicates contracts by `file_name.trim().toLowerCase()`. When it finds the **first row** matching a given file_name, it records that row's `sheet_name` as the contract's sheet. All subsequent rows for the same contract (which may be on different sheets/sections) are skipped via `if (contracts[groupKey]) continue`.

When `_p1fRouteToPreFlight()` is called (line ~18520), it stamps the pre-flight item with the `sheet_name` from that single extracted contract record. The `enrichPreflightItem()` function then resolves `contract_section_label` from this single sheet_name via `canonicalContractSection()`.

**The result:** If the first row for a contract happens to be on an "Accounts" contract section, the pre-flight item is tagged "Accounts" — and no separate pre-flight items are created for Opportunities, Financials, etc., even though those sections also contain data for the same contract.

### What Should Happen
When a contract is flagged (mojibake, non-searchable, etc.), **all contract sections** that contain rows for that contract should receive pre-flight items. The scan should:
1. Identify the contract by file_name (current behavior, correct).
2. Look up ALL contract sections in the workbook that contain rows for that contract.
3. Create a pre-flight item for EACH affected section, not just the first-encountered contract section.

### Files to Audit
| File | Lines | Function |
|------|-------|----------|
| `ui/viewer/index.html` | ~18397–18435 | `_p1fExtractUniqueContracts()` — contract dedup loop; only captures first sheet per contract |
| `ui/viewer/index.html` | ~18440–18520 | `_p1fScanSinglePdf()` — creates mockRecord with single `sheet_name`, passes to route |
| `ui/viewer/index.html` | ~18520–18570 | `_p1fRouteToPreFlight()` — stamps item with the single `sheetName` argument |
| `ui/viewer/index.html` | ~17540–17555 | `enrichPreflightItem()` — resolves `contract_section_label` from `sheet_name` |
| `ui/viewer/index.html` | ~17437–17456 | `_SECTION_CANON` map — section normalization (appears correct, not the root cause) |

### Suggested Fix Approach
In `_p1fScanSinglePdf()`, after a contract is flagged, look up all sheets containing rows for that contract (via `ContractIndex` if available, or by scanning `workbook.sheets`). Then call `_p1fRouteToPreFlight()` once per distinct section, so each section gets its own pre-flight item. The `_p1fExtractUniqueContracts()` function may also need to collect all sheet names per contract rather than just the first.

---

## Issue 2: Schema Snapshot Coverage Gap (173 / 442)

### Observed Behavior
The Schema Snapshot in Triage Analytics shows approximately 173 matched out of 442 total terms (~39% coverage). The glossary (`rules/rules_bundle/field_meta.json`) defines all 442 governed fields, so 100% coverage is expected against a complete workbook.

### Root Cause Hypothesis
The schema matching logic (line ~26264–26365) uses `_fieldMatches(f.field_key, f.field_label)` to check whether each glossary field exists in the workbook. The matching algorithm:

1. Builds `wbCols` from all workbook headers (lowercased and normalized).
2. Builds `wbCanonicals` from `COLUMN_ALIAS_MAP` reverse lookups.
3. Extracts keys from "Fields Definitions" sheets (sheets containing `fields defini` in name).
4. For each glossary field, checks if `field_key` or `field_label` matches any entry in `wbCols` or `wbCanonicals`.

**Potential gaps:**
- **field_meta.json has empty `sheet_name` and `section` fields** (confirmed: all 442 entries have `sheet_name: ""` and `section: ""`). This means the matching cannot use sheet-scoping — it relies entirely on `field_key` and `field_label` string matching.
- **Normalization mismatch**: The `_normKey()` function strips non-alphanumeric characters and lowercases. But if field_meta `field_key` values use Salesforce API naming (e.g., `Account_Name__c`) while workbook headers use human labels (e.g., `Account Name`), the normalized forms may not match unless `COLUMN_ALIAS_MAP` covers them.
- **Missing alias coverage**: If the `COLUMN_ALIAS_MAP` doesn't map all 442 field variants, fields without aliases won't match.
- **Fields Definitions sheet extraction**: The logic looks for sheets with `fields defini` in the name. If the workbook doesn't have such sheets, or if the header detection for `field_api_name` columns fails, those fields won't be added to `wbCols`.

### What Should Happen
All 442 glossary terms should match when a complete workbook is loaded. The matching should account for:
- Direct field_key matches (API names like `Account_Name__c`)
- Label-to-key resolution via aliases
- Fields Definitions sheet extraction for all section-specific definitions sheets
- The `sheet_mapping` in field_meta.json `meta` block (e.g., `"Accounts" → "Accounts Fields Definitions"`)

### Files to Audit
| File | Lines | Function |
|------|-------|----------|
| `ui/viewer/index.html` | ~26260–26370 | `TriageAnalytics.refresh()` — schema matching loop |
| `ui/viewer/index.html` | ~26264 | `cache.schema.standard_total = allFields.length` — total count (442) |
| `ui/viewer/index.html` | ~26350–26360 | `_fieldMatches()` — matching predicate |
| `ui/viewer/index.html` | ~26290–26340 | Fields Definitions sheet extraction — apiIdx/labelIdx detection |
| `rules/rules_bundle/field_meta.json` | entire | Glossary definition — verify `field_key` values and `meta.sheet_mapping` |
| `rules/rules_bundle/column_aliases.json` | entire | Alias map — verify coverage of all 442 fields |

### Suggested Diagnostic Steps
1. Log every unmatched field from the 442 to identify which specific terms are missing.
2. Cross-reference unmatched `field_key` values against `COLUMN_ALIAS_MAP` to find missing aliases.
3. Verify that "Fields Definitions" sheets are being detected and that `apiIdx` is correctly identified.
4. Check if `sheet_mapping` from `field_meta.json` meta is being used during matching.

---

## Issue 3: Contract Count Drift (64 vs 65)

### Observed Behavior
Different parts of the system report inconsistent contract counts:
- The PDF scan banner may show 64 contracts (via `_p1fExtractUniqueContracts()`)
- The ContractIndex may show 65 contracts (via `Object.keys(index.contracts).length`)
- The Triage Analytics header may show either count depending on which source it reads

### Root Cause Hypothesis
Two different contract identification strategies produce different counts:

**`_p1fExtractUniqueContracts()`** (P1F):
- Keys by `file_name.trim().toLowerCase()`
- Skips rows with no `file_url` or `file_name`
- Skips meta/reference/change_log sheets
- Result: Groups by document file, may merge contracts with same filename

**`ContractIndex.build()`**:
- Uses `deriveContractId(row)` which follows a priority chain (file_url hash → contract_key → file_name → fallback signature)
- Groups by derived contract_id, not raw file_name
- Excludes orphan rows (missing URL and name) and header-echo rows
- Result: May split or merge differently than file_name grouping

The 1-contract difference likely comes from either:
- A contract that has a `contract_key`/`contract_id` but no `file_name` (counted by ContractIndex but not P1F)
- A row with a file_url but empty file_name that gets its own ContractIndex entry but is skipped by P1F
- A header-echo row that one system excludes and the other doesn't

### What Should Happen
All contract-counting surfaces should report the same number. One canonical contract counting strategy should be used, or at minimum the counts should be reconciled with an explanation for any delta.

### Files to Audit
| File | Lines | Function |
|------|-------|----------|
| `ui/viewer/index.html` | ~18397–18435 | `_p1fExtractUniqueContracts()` — file_name-based counting |
| `ui/viewer/index.html` | ~7000–7110 | `ContractIndex.build()` — priority-chain contract ID derivation |
| `ui/viewer/index.html` | ~7880–7895 | `datasetWideCount` — grid stat contract count |
| `ui/viewer/index.html` | ~26170–26180 | `TriageAnalytics.refresh()` — `cache.total_contracts` sourcing |
| `ui/viewer/index.html` | ~17597–17612 | P1D.1 `_uniqueContracts` — affected contract counting in pre-flight table |
| `ui/viewer/index.html` | ~2055 | Count mismatch warning badge — `&#9888; Count mismatch` |

### Suggested Diagnostic Steps
1. Log the contract IDs from both `_p1fExtractUniqueContracts()` and `ContractIndex.listContracts()` side by side.
2. Identify the contract(s) present in one set but not the other.
3. Trace why the missing contract's rows fail the inclusion criteria of the system that omits it.
4. Determine which count is "correct" and align the other system.

---

## Cross-Cutting Concerns

### Interaction Between Issues
These three issues may compound each other:
- If the contract count is wrong (Issue 3), the "Affected Contracts" metric in Pre-Flight (Issue 1) may also be wrong.
- If schema matching misses fields (Issue 2), pre-flight items that should trigger for those fields won't fire.
- If pre-flight items only show "Accounts" section (Issue 1), the contract health score (P1G) may under-penalize contracts that have issues in other sections.

### Audit Deliverables Expected
1. **Root cause confirmation** for each of the 3 issues with specific line references.
2. **Unmatched field list** — the ~269 fields from field_meta.json that don't match, with reasons.
3. **Contract diff** — which contract(s) cause the 64 vs 65 discrepancy.
4. **Fix recommendations** with estimated scope for each issue.
5. **Regression risk assessment** — what could break if fixes are applied.

---

## Reference: Key Data Points

| Metric | Current | Expected |
|--------|---------|----------|
| Contract sections in Pre-Flight | 1 (Accounts only) | All sections with data (Accounts, Opportunities, Financials, Catalog, etc.) |
| Schema terms matched | ~173 / 442 (39%) | 442 / 442 (100%) |
| Contract count consistency | 64 in some views, 65 in others | Single consistent count across all views |
| Glossary fields defined | 442 | 442 |
| `_SECTION_CANON` entries | 18 aliases → 8 sections | Verified correct |
