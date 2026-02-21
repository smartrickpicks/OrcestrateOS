# V2.3 Gate Verification Runbook

Deterministic steps for verifying each gate (G1–G9). Open browser DevTools Console before starting.

## Prerequisites

- App loaded at `/ui/viewer/`
- DevTools Console open, filtered to `[V2.3-GATE]`
- Test XLSX file with: multiple contracts (file_url values), unknown columns, header-echo rows, rows missing file_url

---

## G1 — Contract ID Derivation Priority

**Setup:** Prepare XLSX with rows containing `file_url` values (some with extractable path IDs, some without).

**Action:** Upload the XLSX file via "Add Data Source".

**Assertion:** Console shows the derivation source for the first contract processed.

**Expected log:**
```
[V2.3-GATE][G1] PASS contract_id derived via priority chain: source=extracted id=ctr_...
```

---

## G2 — ContractIndex Rebuild on All Load Paths

**Setup:** App loaded.

**Action (upload):** Upload an XLSX file.
**Action (demo):** Click "Load Demo Dataset" from data source panel.
**Action (session):** Reload the page (session auto-restore).
**Action (restore):** Use session restore from saved sessions.

**Assertion:** Each path emits its own G2 log.

**Expected logs (one per path used):**
```
[V2.3-GATE][G2] PASS ContractIndex rebuilt from live workbook on upload path
[V2.3-GATE][G2] PASS ContractIndex rebuilt from live workbook on demo/sandbox path
[V2.3-GATE][G2] PASS ContractIndex rebuilt from live workbook on session-load path
[V2.3-GATE][G2] PASS ContractIndex rebuilt from live workbook on restore path
```

---

## G3 — Threshold Consistency

**Setup:** Upload file with unknown columns.

**Action:** ContractIndex builds and routes unknown columns.

**Assertion:** Thresholds match locked values.

**Expected log:**
```
[V2.3-GATE][G3] PASS thresholds locked: warn>0 blocker>3
```

**Additional verification:** In Triage → Pre-Flight, unknown columns with 1–3 non-empty values show `severity: warning`; columns with >3 show `severity: blocker`.

---

## G4 — Unknown Column Frequency Vote Routing

**Setup:** Upload file with unknown columns across contract sections with contract data.

**Action:** ContractIndex builds.

**Assertion:** Unknown columns are routed via contract-section-scoped frequency vote.

**Expected log:**
```
[V2.3-GATE][G4] PASS unknown-column routing: N entries routed via sheet-scoped frequency vote
```

---

## G5 — Header-Echo Sanitization

**Setup:** Prepare CSV or XLSX where some data rows duplicate the header values (>= 60% token overlap).

**Action:** Upload the file.

**Assertion:** Header-echo rows are removed at parse time; audit event emitted.

**Expected log:**
```
[V2.3-GATE][G5] PASS header-echo sanitized: N rows removed from CSV
```
or
```
[V2.3-GATE][G5] PASS header-echo sanitized: N rows removed, sheet=SheetName
```

**Audit event:** `ROW_SANITIZED_HEADER_ECHO` with `metadata: { sheet_name, row_index, match_ratio }`.

---

## G6 — Storage Policy (IndexedDB Only)

**Setup:** Upload any file.

**Action:** Workbook is cached after load.

**Assertion:** Workbook saved to IndexedDB, no localStorage blob writes.

**Expected log:**
```
[V2.3-GATE][G6] PASS workbook saved to IndexedDB only, no localStorage blobs
```

**Additional verification:** In DevTools Application → Local Storage, no key contains large dataset blobs. `orchestrate.dataset.v1` key should not exist.

---

## G7 — Contract Selector Dataset-Wide

**Setup:** Upload file with contracts across multiple contract sections.

**Action:** Change contract section filter in the grid.

**Assertion:** Contract count in the stat badge and dropdown total remain stable across contract section changes.

**Expected log:**
```
[V2.3-GATE][G7] PASS contract count dataset-wide: N contracts across all contract sections
```

---

## G8 — Missing URL Orphan Handling

**Setup:** Upload file where some rows have no `file_url` and no `file_name`/`contract_key`.

**Action:** ContractIndex builds.

**Assertion:** Orphan rows counted but not assigned to any contract.

**Expected log:**
```
[V2.3-GATE][G8] PASS missing-URL rows: N orphaned to batch-level (reason=missing_url_and_name)
```

---

## G9 — Unknown Column Payload Completeness

**Setup:** Upload file with unknown columns.

**Action:** ContractIndex routes unknown columns.

**Assertion:** Audit event payload includes all required fields.

**Expected log:**
```
[V2.3-GATE][G9] PASS unknown-column payload complete: batch_id=... sheet=... contract_id=... source=... confidence=...
```
