# 02 — Data Identity, Contract Resolution, and Salesforce Matching

## Who This Is For

Anyone who needs to understand how Orchestrate OS identifies records, builds contract hierarchies, matches data to Salesforce records, and ensures no data gets silently lost or misattributed.

## 1. How Records Are Identified

Every record in Orchestrate OS has a four-part identity:

| Field | Purpose | Example |
|-------|---------|---------|
| `tenant_id` | Which organization owns this data | `cmg` (Create Music Group) |
| `division_id` | Which division within the organization | `cmg_recorded` |
| `dataset_id` | Which batch/workbook this came from | `Broke_Aug_2025_Kiwi_Extraction` |
| `record_id` | Unique identifier for this specific row | `rec_01HX...` |

This four-part key ensures that even if two organizations upload files with identical row data, the system keeps them completely separate.

## 2. The Join Strategy (How Stages Connect)

When data moves from one pipeline stage to the next, stages need to know which records they're talking about. The join strategy is strict and transparent:

**Join order (fallback chain):**
1. `contract_key` — The primary join field. Most reliable.
2. `file_url` — If contract_key is missing, fall back to the file URL.
3. `file_name` — Last resort. Join on the filename.

**Critical rules:**
- **No fabrication.** If a join field is missing, the system does not guess or generate one. It flags the issue.
- **No silent joins.** If a record can't be joined, it surfaces as an orphan — visible in the UI, not hidden.
- **Nulls sort last.** Records with missing join fields appear at the end, making them easy to spot.

## 3. The Contract Index Engine

The Contract Index Engine builds a navigable hierarchy from flat spreadsheet data:

```
Batch (the uploaded workbook)
  └── Contract (derived from file_url or file_name)
        └── Document (an individual file/PDF within the contract)
              └── Section (a sheet: Accounts, Finance, Catalog, etc.)
                    └── Row (a single data record)
```

**How contracts are derived:**
- The engine looks at the `file_url` or `file_name` column in each row
- Rows sharing the same file URL/name are grouped into the same contract
- This means a single workbook can contain multiple contracts if it references multiple source files

**Orphan rows:**
- Rows that can't be attributed to any contract are collected as orphan rows
- Orphan rows are excluded from contract lifecycle tracking but remain visible
- The Triage view shows orphan counts so analysts can investigate

## 4. Contract Health Scoring

Each contract receives a health score from 0 to 100, calculated by the Contract Health Score engine:

| Band | Score Range | Meaning |
|------|-------------|---------|
| **Critical** | 0-25 | Major blockers present, contract cannot advance |
| **At Risk** | 26-50 | Significant issues need attention |
| **Watch** | 51-75 | Minor issues, progressing but needs monitoring |
| **Healthy** | 76-100 | On track, few or no outstanding issues |

The score factors in:
- Number of unresolved pre-flight blockers
- Outstanding signals (MISSING_REQUIRED, OCR_UNREADABLE)
- Patch submission and approval status
- RFI resolution status

## 5. Batch Merge

When an analyst needs to combine data from multiple source batches into a single governance container, the Batch Merge feature handles this:

- Multiple source batches are selected
- The system combines them into a unified batch, preserving provenance
- Duplicate detection runs across the merged data
- Tenant-specific rules are explicitly promoted (not silently inherited)

This is important when a record label receives contract data from multiple sources (different divisions, different extraction runs) and needs to govern it as a single unit.

## 6. Column Alias Resolution

Music industry data comes in many formats. Different systems call the same field by different names. The column alias system handles this:

- **479 alias entries** map variant column names to canonical names
- Example: `Account_Name__c`, `account_name`, `ACCOUNT_NAME`, `AcctName` all resolve to the canonical `account_name`
- The `COLUMN_ALIAS_MAP` is used by the Triage Analytics engine for schema matching
- Conflicts are logged when the same alias could map to different canonical names across different sheets

**Pre-flight check:** If a column header can't be resolved through the alias map, it's flagged as an unknown column in pre-flight. The analyst must either map it or confirm it should be ignored.

## 7. Salesforce Matching

Orchestrate OS sits upstream of Salesforce. One of its jobs is ensuring that contract data can be confidently matched to the right Salesforce records before it's pushed downstream.

### What We're Matching

For each row in the workbook, we need to answer: **"Which Salesforce record does this belong to?"**

The answer depends on the object type:

| Object | Key Matching Fields |
|--------|-------------------|
| **Account** | account_name, billing_country, billing_city |
| **Opportunity** | opportunity_id, opportunity_name, account_name |
| **Contact** | contact_name, email, account_name |
| **ContentDocument** | content_document_id, content_version_id |

### Confidence Scoring

Confidence is a simple, transparent metric:

- Compare inbound row values against expected Salesforce record values
- Count how many key fields match
- **3/3 match** → High confidence (safe to proceed)
- **2/3 match** → Medium confidence (review recommended)
- **1/3 match** → Low confidence (manual verification required)

Confidence must be explainable. Operators see exactly which fields matched and which didn't.

### Subtype-Driven Schema

The `subtype` field determines what data should exist for a given record:

- `record_label` subtype → expect label-like company fields, do NOT expect artist_name
- `publishing` subtype → expect writer/composition fields
- `distribution` subtype → expect catalog and territory fields

Subtype drives two things:
1. **Schema expectations** — which fields should be present vs. blank
2. **Match strategy** — which fields matter most for confidence scoring

## 8. The Resolver (Contract File Resolution)

The Resolver answers one question: **"Where do I download this contract file from?"**

### Pointer Precedence

The Resolver tries pointer types in order:
1. **Direct web link** (`file_url`) — fastest, simplest
2. **Salesforce IDs** (ContentVersion / ContentDocument / Opportunity) — requires SF credentials
3. **S3 location** (bucket + key) — requires presigned URL
4. **Google Drive** — v2.5 addition; files can now be imported directly from connected Google Drive folders

### When Resolution Fails

`NO_RESOLVABLE_POINTERS` means none of the pointer types are available. Quick fixes:
- Add a working `file_url` in the dataset row
- Provide Salesforce IDs that point to the file
- Import the file directly from Google Drive

### Google Drive as a Source (v2.5)

With Google Drive integration, analysts can:
1. Connect their workspace to Google Drive via OAuth
2. Browse a shared contracts folder (root folder configurable via `DRIVE_ROOT_FOLDER_ID` environment variable)
3. Navigate folder hierarchies with breadcrumbs
4. Select and import spreadsheets (xlsx, xls, csv) directly
5. The imported file's provenance (Drive file ID, folder, import timestamp) is recorded in the `drive_import_provenance` table

This gives analysts a way to resolve contracts without needing direct URLs or Salesforce IDs.

## 9. Data Quality Check (Combined Interstitial)

After a workbook loads, a combined data quality check fires automatically. This unified modal handles:

1. **Duplicate Account Detection** — Finds account pairs that look like duplicates based on normalized field comparison
2. **Incomplete Address Candidate Matching** — The `ADDRESS_INCOMPLETE_CANDIDATE` system uses deterministic candidate matching to find records with partial address data and suggest completions

Results route to Pre-Flight as either warnings (proceed with caution) or blockers (must resolve before advancing).

## 10. Troubleshooting Checklist

When data looks wrong or a contract is stuck, check in this order:

### A. Was the workbook loaded?
Check the Triage dashboard. If it shows 0 records, the workbook didn't parse. Check for unsupported file format or corrupted file.

### B. Did pre-flight pass?
Check the Pre-Flight section in Triage. If there are blockers (unknown columns, OCR issues, duplicate accounts, incomplete addresses), they must be resolved first.

### C. Are signals generated?
Check the signal count in the Triage header. If 0, either the data is clean or the rules bundle didn't load. Check the browser console for `[SignalEngine]` logs.

### D. Is the contract indexed?
Check the Contract Summary. If it shows 0 contracts, the Contract Index Engine couldn't derive contracts from the data — likely because `file_url` or `file_name` columns are missing or empty.

### E. Can records be matched to Salesforce?
If confidence is low across the board, check whether the subtype is set correctly and whether the expected matching fields are populated.

### F. Is the Drive connection active?
If Drive import/export isn't working, check the Drive status in the Data Source panel. The OAuth token may have expired — use the Refresh button to reconnect.
