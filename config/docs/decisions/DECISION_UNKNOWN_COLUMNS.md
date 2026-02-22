# Decision Memo: Unknown Column Routing

**Version:** 2.3  
**Status:** Locked

## Threshold Behavior

- **Warning**: Any unknown column with >0 non-empty values is flagged as a warning
- **Blocker**: Unknown columns with >3 non-empty values are elevated to blocker severity

## Attachment Routing

Unknown columns are attached to contracts or batches using a **contract-section-scoped frequency vote**:

1. For each contract section containing unknown columns, derive `contract_id` for every row
2. Count votes per contract ID
3. Attach to the top-voted contract only if:
   - `top_share >= 60%` (top contract has ≥60% of all voted rows), OR
   - `top_count >= 2× second_count` (top contract has at least double the second)
4. Otherwise, attach at **batch level**

## Audit Event Payload

Every `UNKNOWN_COLUMN_DETECTED` event includes:
- `batch_id` (always)
- `sheet` (always)
- `contract_id` (nullable — null when batch-level)
- `contract_id_source` (nullable — derivation method when contract-level)
- `attach_confidence` (0-100, percentage of rows voting for the attached contract)
- `severity` (warning or blocker)
