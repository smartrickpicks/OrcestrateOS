# Decision Memo: Storage Policy

**Version:** 2.3  
**Status:** Locked

## localStorage Usage

localStorage is reserved for lightweight preferences and pointers only:

- Role selection, filter states, UI preferences
- Pointers to IndexedDB entries (e.g., `orchestrate_idb_workbook_ptr`)
- Small config flags

## Prohibited in localStorage

- Workbook data (contract section rows, headers)
- Dataset blobs (`allData`, `contractResults`)
- Any payload exceeding ~10KB

## Payload Storage

All workbook and dataset payloads are persisted to **IndexedDB** via `SessionDB`:

- `saveWorkbookCache()` → IndexedDB only
- `saveSession()` → IndexedDB only
- ContractIndex references → IndexedDB with localStorage pointer

## Rationale

localStorage has a ~5MB limit per origin. Large datasets easily exceed this, causing silent failures. IndexedDB has effectively unlimited storage and supports structured data.
