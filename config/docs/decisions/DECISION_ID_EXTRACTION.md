# Decision Memo: ID Extraction & URL Canonicalization

**Version:** 2.3  
**Status:** Locked

## Contract ID Derivation Priority

1. **Extracted path ID** (`source: extracted`): Extract the last path segment from the canonical URL after stripping query/hash. Hash it.
2. **URL hash** (`source: url_hash`): Hash the full canonical URL when path extraction yields nothing usable.
3. **Fallback signature** (`source: fallback_sig`): Hash `file_name` or `contract_key` when no URL is present.

Every contract entry persists `contract_id_source` for auditability.

## URL Canonicalization Steps

1. Trim whitespace
2. Strip trailing slashes
3. Remove query string and fragment
4. `decodeURIComponent`
5. Lowercase

## Orphan Policy

Rows with no valid URL and no valid name are classified as batch-level orphans (`reason: missing_url_and_name`). They are never force-assigned to a contract.

## Config Reference

See `config/id_extraction_rules.json` for machine-readable rules.
