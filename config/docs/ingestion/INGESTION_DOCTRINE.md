# Ingestion Doctrine

Audience: Operators and governance verifiers
Purpose: Define inbound/outbound conventions, attribution patterns, and routing rules
Scope: Docs-only; offline-first governance contracts
Non-Goals: No runtime implementation claims; no external service integrations
Authority Level: Governance doctrine; implementation must conform
Owner Agent: Kiwi (documentation architect)
Update Rules: Changes require governance review; link evidence for any claimed implementation

## Folder Conventions

### Inbound Folder
- Path: `inbound/` (repo-relative)
- Purpose: Staging area for new submissions awaiting ingestion
- Structure: Flat files or per-user subfolders (see Attribution Patterns)
- File types: CSV, XLSX, JSON, PDF (attachments)

### Outbound Folder
- Path: `outbound/` (repo-relative)
- Purpose: Published outputs after Admin Approval
- Structure: Timestamped subfolders per export batch
- Naming: `outbound/YYYY-MM-DD_HHMMSS/`

### Archive Folder
- Path: `archive/` (repo-relative)
- Purpose: Immutable record of processed submissions
- Retention: Configurable; default indefinite

## Attribution Patterns

### Pattern A: Per-User Folders
```
inbound/
├── alice/
│   └── contracts_2026-02.xlsx
├── bob/
│   └── catalog_update.csv
└── charlie/
    └── royalties_q1.json
```
- Attribution: Folder name = submitter identity
- Pros: Simple, self-organizing
- Cons: Requires folder-per-user provisioning

### Pattern B: Manifest File
```
inbound/
├── contracts_2026-02.xlsx
├── catalog_update.csv
└── manifest.json
```
Manifest schema:
```json
{
  "submissions": [
    {
      "file": "contracts_2026-02.xlsx",
      "submitter": "alice@example.com",
      "submitted_at": "2026-02-02T10:30:00Z",
      "checksum_sha256": "abc123..."
    }
  ]
}
```
- Attribution: Explicit in manifest
- Pros: No folder structure requirements
- Cons: Manifest must be maintained

### Decision Status
- Pattern choice: Unknown — requires audit
- Auth integration for submitter identity: Unknown — requires audit (V2)

## Routing Rules by Review State

| Source Condition | Target Review State | Assigned To |
|------------------|---------------------|-------------|
| New submission, no issues | To Do | Analyst pool |
| Blocking rule triggered | Blocked | Analyst pool |
| Analyst submits patch request | Needs Review | Verifier pool |
| Verifier approves | Finalized | (none) |
| Verifier requests clarification | Flagged | Original Analyst |

### Routing Logic (Docs-Only)
1. Ingestion registers file → INGESTION_REGISTERED event
2. Attribution resolved → SUBMISSION_ATTRIBUTED event
3. Initial Review State assigned → ROUTED_TO_ANALYST event
4. After Admin Approval → OUTPUT_PUBLISHED event

## Checksum and Audit Requirements

### Checksum Policy
- Algorithm: SHA-256
- Scope: All ingested files at registration time
- Storage: Audit log payload and/or manifest

### Audit Expectations
- Every ingested file must have a recorded checksum
- Checksum verified on archive retrieval
- Mismatch triggers integrity alert (V2)

## Source Types

### V1: Local Folder (Implemented)
- Inbound folder watched locally
- Manual file placement
- Offline-compatible

### V2 Stubs (Not Implemented)

> **Note:** The following are governance stubs only. No runtime integration exists.

#### Google Drive Drop (V2 Stub)
- Status: Not implemented
- Purpose: Auto-ingest from shared Drive folder
- Requires: OAuth integration, folder watch API

#### Dropbox Drop (V2 Stub)
- Status: Not implemented
- Purpose: Auto-ingest from Dropbox folder
- Requires: Dropbox API integration

#### Email Drop (V2 Stub)
- Status: Not implemented
- Purpose: Ingest attachments from dedicated mailbox
- Requires: IMAP/SMTP integration, attachment extraction

## References
- docs/AUDIT_LOG.md — event type definitions
- docs/ui/views/data_source_view.md — UI surface for source management
- docs/overview.md — system overview
