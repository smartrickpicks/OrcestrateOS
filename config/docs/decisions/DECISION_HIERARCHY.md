# Decision Memo: Contract Hierarchy

**Version:** 2.3  
**Status:** Locked

## Hierarchy

```
batch → contract → document → sheet → row
```

- **Batch**: A single upload/import session. Identified by `dataset_id`.
- **Contract**: Grouped by canonical file URL or fallback signature. Identified by `contract_id`.
- **Document**: Unique by full URL. One contract may contain multiple documents (amendments, schedules).
- **Contract Section**: A section within the workbook containing rows for a document.
- **Row**: Individual record with `record_id`.

## Identity Fields

Record identity is defined by: `tenant_id`, `division_id`, `dataset_id`, `record_id`.

## ContractIndex Rebuild Policy

ContractIndex is always recomputed from the live workbook on every load path (upload, restore, session load). Session-stored references are used only as pointers, never as authoritative data.
