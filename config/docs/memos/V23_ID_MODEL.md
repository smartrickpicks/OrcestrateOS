# V2.3 Identity Model (Locked)

## Hierarchy

```
Tenant
  └── Legal Entity (implicit from dataset context)
        └── Batch (workbook upload or merge container)
              └── Contract (derived from file_url / file_name)
                    └── Document (derived from file_url + contract section context)
                          └── Record (row-level, per contract section)
```

## ID Derivation

### batch_id
- Format: `batch_{timestamp}_{random}`
- Created once per `ContractIndex.build()` invocation.
- Stable within a session; regenerated on rebuild.

### contract_id
- Derived by `ContractIndex.deriveContractId(row, returnMeta)`.
- Priority chain (G1):
  1. **Extracted path ID** — file identifier extracted from canonical URL via `_extractFileIdentifier()` → `ctr_{hash(fileId)}`, `source=extracted`
  2. **URL hash** — hash of full canonical URL → `ctr_{hash(canonUrl)}`, `source=url_hash`
  3. **Fallback signature** — hash of file_name or contract_key → `ctr_{hash(fileName)}`, `source=fallback_sig`
- `contract_id_source` persisted per contract in the index for audit traceability.

### URL Canonicalization
- Trim whitespace
- Strip trailing slashes
- Remove query string and hash fragment
- `decodeURIComponent`
- Lowercase

### document_id
- Derived by `ContractIndex.deriveDocumentId(row)`.
- Combines file_url (or file_name) with contract section context.
- Format: `doc_{hash(combined)}`.

### record_id
- From `row.record_id` or `row._identity.record_id` or `row_{rowIdx}` fallback.
- Scoped to contract section within a document.

## Identity Context

Record identity is defined by the tuple:
- `tenant_id` — from dataset metadata
- `division_id` — from dataset metadata
- `dataset_id` — from dataset metadata or derived
- `record_id` — per-row identifier

Stored in the global `IDENTITY_CONTEXT` object, set on dataset load.

## Orphan Handling (G8)

Rows with no valid `file_url` and no valid `file_name`/`contract_key` are orphaned:
- Not assigned to any contract.
- Pushed to `index.orphan_rows` with `reason: 'missing_url_and_name'`.
- Default to batch-level in reporting.

## Cross-References

- `docs/decisions/DECISION_ID_EXTRACTION.md` — full decision record
- `docs/decisions/DECISION_HIERARCHY.md` — hierarchy and rebuild policy
- `config/id_extraction_rules.json` — machine-readable extraction rules
