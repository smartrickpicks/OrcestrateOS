# V2.54 Annotation Layer Artifact Specification

**Version:** 2.54  
**Date:** 2026-02-17  
**Status:** LOCKED — Clarity Phase  
**Scope:** Canonical definition of Annotation Layer artifacts for Verifier/Admin governance  

---

## 1. Authoritative Decision

The **Annotation Layer** is a first-class artifact system and the canonical governance truth for all Verifier and Admin operations.

- Source documents (PDFs, XLSX sheets) are **context-only** — they inform decisions but are never the governance record.
- If a source document is unavailable (deleted, expired, moved), the Annotation Layer still provides a complete, self-contained record of all governance decisions, evidence, and custody chains.
- All verifier and admin actions MUST write to the DB Annotation Layer. Client-side localStorage is a temporary transition fallback only and is NEVER canonical.

---

## 2. Annotation Artifact Definition

### 2.1 Core Identity Fields

Every annotation artifact carries these identity fields:

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `id` | TEXT (ULID-prefixed) | Primary key. Prefix indicates type: `pat_`, `rfi_`, `cor_`, `anc_`, `ann_`, `sel_` | Yes |
| `workspace_id` | TEXT | FK → `workspaces.id`. Isolation boundary. | Yes |
| `batch_id` | TEXT | FK → `batches.id`. Nullable for workspace-level artifacts. | Conditional |
| `contract_id` | TEXT | FK → `contracts.id`. Nullable. | Conditional |
| `document_id` | TEXT | FK → `documents.id`. Required for anchors, corrections, selections. | Conditional |
| `record_id` | TEXT | Logical record identifier (from imported workbook row). | Conditional |
| `field_key` | TEXT | Target field within a record. | Conditional |

### 2.2 Lifecycle and Custody Fields

| Field | Type | Description | Required |
|-------|------|-------------|----------|
| `status` | TEXT | Resource-specific lifecycle status (see §3) | Yes |
| `custody_status` | TEXT | Who currently owns the action item (RFIs only, see §3.2) | Conditional |
| `custody_owner_id` | TEXT | FK → `users.id`. Current custody holder. | Conditional |
| `custody_owner_role` | TEXT | Role of custody holder: `analyst`, `verifier`, `admin` | Conditional |
| `author_id` / `created_by` | TEXT | FK → `users.id`. Original creator. | Yes |
| `decided_by` | TEXT | FK → `users.id`. Actor who made the governance decision. | Conditional |
| `created_at` | TIMESTAMPTZ | Creation timestamp (UTC). | Yes |
| `updated_at` | TIMESTAMPTZ | Last modification timestamp (UTC). | Yes |
| `resolved_at` / `decided_at` | TIMESTAMPTZ | When the governance decision was finalized. | Conditional |
| `deleted_at` | TIMESTAMPTZ | Soft-delete timestamp. NULL = active. | No |
| `version` | INTEGER | Optimistic concurrency version. Increments on every update. | Yes |
| `metadata` | JSONB | Extensible metadata bucket. | Yes (default `{}`) |

### 2.3 Linkage Model

Artifacts form a directed graph of governance relationships:

```
batch
  └── contract
        └── document
              ├── anchor (text selection in source doc)
              │     └── correction (field-level fix linked to anchor)
              └── selection_capture (evidence screenshot/region)

patch (workspace-scoped, optionally batch-scoped)
  ├── evidence_pack (structured evidence blocks)
  ├── rfi (request for information, linked to patch OR standalone)
  └── annotation (note/flag/question on patch or record)
        └── annotation_link (links annotation to patch/rfi/evidence_pack/selection)

audit_event (append-only chronicle of all governance actions)
```

### 2.4 Lineage Pointers

Each artifact type carries specific foreign keys that establish lineage:

| Artifact | Lineage Pointers | Description |
|----------|-----------------|-------------|
| **Patch** (`patches`) | `batch_id`, `record_id`, `field_key`, `evidence_pack_id`, `author_id` | Central governance unit. Links to batch context, record target, and evidence. |
| **RFI** (`rfis`) | `patch_id` (nullable), `target_record_id`, `target_field_key`, `author_id`, `responder_id` | Clarification request. May be standalone or linked to a patch. |
| **Correction** (`corrections`) | `document_id`, `anchor_id` (nullable), `rfi_id` (nullable), `field_id`, `field_key`, `created_by`, `decided_by` | Field-level fix, linked to document and optionally to anchor/RFI evidence. |
| **Anchor** (`anchors`) | `document_id`, `node_id`, `field_id`, `field_key`, `created_by` | Text anchor in source document. Deduplicated by `anchor_fingerprint`. |
| **Annotation** (`annotations`) | `target_type` + `target_id`, `author_id` | Note/flag/question attached to field, record, contract, or document. |
| **Annotation Link** (`annotation_links`) | `annotation_id`, `linked_type` + `linked_id` | Junction table linking annotations to patches, RFIs, evidence packs, or selections. |
| **Evidence Pack** (`evidence_packs`) | `patch_id`, `author_id` | Structured evidence blocks supporting a patch. |
| **Selection Capture** (`selection_captures`) | `document_id`, `field_id` (nullable), `rfi_id` (nullable), `author_id` | Region/text capture from a document page. |
| **Audit Event** (`audit_events`) | `workspace_id`, `batch_id`, `record_id`, `field_key`, `patch_id`, `actor_id` | Append-only. Immutable chronicle. |

### 2.5 Batch Linkage Strategy

| Artifact | Current batch_id column | Batch linkage path |
|----------|------------------------|--------------------|
| Patch | `patches.batch_id` (nullable FK) | Direct |
| RFI | **Not present** | Via `rfis.patch_id → patches.batch_id` (indirect, nullable) |
| Correction | Not present | Via `corrections.document_id → documents.batch_id` (indirect, always present) |
| Anchor | Not present | Via `anchors.document_id → documents.batch_id` (indirect, always present) |
| Triage Item | `triage_items.batch_id` (required FK) | Direct |
| Signal | `signals.batch_id` (required FK) | Direct |
| Audit Event | `audit_events.batch_id` (nullable) | Direct when populated |

**Decision Required (VER-04):** Whether to add a `batch_id` column to `rfis` for direct batch linkage. See §4.

---

## 3. Artifact Lifecycle Models

### 3.1 Patch Lifecycle (12-status)

```
Draft → Submitted → Needs_Clarification → Verifier_Responded → Verifier_Approved → Admin_Approved → Applied
                  → Rejected                                  → Rejected
                  → Cancelled             → Cancelled          → Admin_Hold → Admin_Approved
                                                                            → Rejected
                                                               → Sent_to_Kiwi → Kiwi_Returned → Admin_Approved
                                                                                               → Rejected
```

**Transition matrix** (from `patches.py` L26–48):

| From | To | min_role | author_only | self_approval_check |
|------|----|----------|-------------|---------------------|
| Draft | Submitted | analyst | Yes | No |
| Draft | Cancelled | analyst | Yes | No |
| Submitted | Needs_Clarification | verifier | No | No |
| Submitted | Verifier_Approved | verifier | No | **Yes** |
| Submitted | Rejected | verifier | No | No |
| Submitted | Cancelled | analyst | Yes | No |
| Needs_Clarification | Verifier_Responded | analyst | Yes | No |
| Needs_Clarification | Cancelled | analyst | Yes | No |
| Verifier_Responded | Verifier_Approved | verifier | No | **Yes** |
| Verifier_Responded | Needs_Clarification | verifier | No | No |
| Verifier_Responded | Rejected | verifier | No | No |
| Verifier_Responded | Cancelled | analyst | Yes | No |
| Verifier_Approved | Admin_Approved | admin | No | **Yes** |
| Verifier_Approved | Admin_Hold | admin | No | No |
| Verifier_Approved | Cancelled | analyst | Yes | No |
| Admin_Hold | Admin_Approved | admin | No | **Yes** |
| Admin_Hold | Rejected | admin | No | No |
| Admin_Approved | Applied | admin | No | No |
| Admin_Approved | Sent_to_Kiwi | admin | No | No |
| Sent_to_Kiwi | Kiwi_Returned | admin | No | No |
| Kiwi_Returned | Admin_Approved | admin | No | No |
| Kiwi_Returned | Rejected | admin | No | No |

### 3.2 RFI Custody Lifecycle

**Status field:** `rfis.status` — `open`, `responded`, `closed`  
**Custody field:** `rfis.custody_status` — `open`, `awaiting_verifier`, `returned_to_analyst`, `resolved`, `dismissed`

Custody transition matrix (from `rfis.py` L20–26):

| From | To | Allowed Roles |
|------|----|---------------|
| open | awaiting_verifier | analyst |
| awaiting_verifier | returned_to_analyst | verifier, admin |
| awaiting_verifier | resolved | verifier, admin |
| awaiting_verifier | dismissed | verifier, admin |
| returned_to_analyst | awaiting_verifier | analyst |

Custody owner tracking (from migration 007):
- `custody_owner_id`: The user who currently holds custody
- `custody_owner_role`: `analyst` (when open/returned), `verifier` (when awaiting_verifier), NULL (when resolved/dismissed)

### 3.3 Correction Lifecycle

**Status field:** `corrections.status` — `pending_verifier`, `approved`, `rejected`  
**Decision fields:** `decided_by`, `decided_at`

Transition matrix (from `corrections.py` L30–35):

| From | To | Allowed Roles |
|------|----|---------------|
| pending_verifier | approved | verifier, admin |
| pending_verifier | rejected | verifier, admin |

### 3.4 Anchor Lifecycle

Anchors are immutable after creation. They can be soft-deleted (`deleted_at` set) but not modified. The `anchor_fingerprint` UNIQUE constraint prevents duplicate anchors for the same text selection.

### 3.5 Annotation Lifecycle

Annotations support update (via `PATCH /annotations/{id}`) and soft-delete. No formal status lifecycle — they are notes/flags/questions that can be edited or removed.

---

## 4. Data Precedence (Canonical)

This is the authoritative data precedence order for all Verifier and Admin operations:

| Priority | Layer | Description | Governance Role |
|----------|-------|-------------|----------------|
| **P0** | **DB Annotation Layer** | RFIs, Corrections, Anchors/Evidence Marks, Patch lifecycle, Audit events, Annotations | **Canonical governance truth.** All decisions read and write here. |
| P1 | Imported Workbook Snapshot | Row/field data from CSV/XLSX import, stored in batch/contract/document/account tables | **Baseline context only.** Provides the original values that patches propose to change. Never modified by verifier actions. |
| P2 | Drive Metadata/Provenance | Google Drive file metadata, folder routing, export history (`drive_import_provenance`, `drive_export_history`) | **Storage metadata only.** Tracks where files came from and where exports went. Never governs decisions. |
| P3 | localStorage | `verifierQueueState`, `PATCH_REQUEST_STORE`, `ARTIFACT_STORE` | **Temporary transition fallback only.** Never canonical. Will be removed after migration to DB-first reads. |

### 4.1 Conflict Resolution

- **DB vs localStorage divergence:** DB always wins. UI must hydrate from DB on page load.
- **Stale version on PATCH:** Server returns 409 `STALE_VERSION`. Client must refetch and retry.
- **Source document unavailable:** Annotation cards still render, verifier workflow still functions. The annotation layer is self-contained.

---

## 5. Existing DB Schema Summary

### 5.1 Tables by Migration

| Migration | Tables Created/Modified | Annotation Relevance |
|-----------|------------------------|---------------------|
| 001_core_tables | `workspaces`, `users`, `user_workspace_roles`, `batches`, `accounts`, `contracts`, `documents`, `patches`, `evidence_packs`, `annotations`, `annotation_links`, `rfis`, `triage_items`, `signals`, `selection_captures`, `audit_events`, `api_keys`, `idempotency_keys` | Core annotation schema |
| 005_evidence_inspector_v251 | `anchors`, `corrections`, `reader_node_cache`, `ocr_escalations` + `rfis.custody_status` | Evidence layer |
| 006_anchors_selected_text_hash | `anchors.selected_text_hash` | Anchor dedup |
| 007_rfi_custody_owner | `rfis.custody_owner_id`, `rfis.custody_owner_role` | RFI custody tracking |

### 5.2 Index Coverage

All annotation tables have workspace-scoped indexes. Key indexes:
- `idx_patches_workspace(workspace_id)`, `idx_patches_status(workspace_id, status)`, `idx_patches_author(workspace_id, author_id)`
- `idx_rfis_workspace(workspace_id)`, `idx_rfis_patch(workspace_id, patch_id)`
- `idx_corrections_workspace(workspace_id)`, `idx_corrections_status(status)`, `idx_corrections_anchor_id(anchor_id)`
- `idx_anchors_workspace_id(workspace_id)`, `idx_anchors_document_id(document_id)`
- `idx_annotations_target(workspace_id, target_type, target_id)`
- `idx_audit_events_workspace(workspace_id)`, `idx_audit_events_timestamp(workspace_id, timestamp_iso)`

### 5.3 Missing Indexes (Recommended for Operations View)

| Table | Recommended Index | Rationale |
|-------|------------------|-----------|
| `patches` | `idx_patches_batch(workspace_id, batch_id)` | Batch-scoped patch queries for Operations View |
| `patches` | `idx_patches_record(workspace_id, record_id)` | Record-scoped patch queries for verifier review |
| `rfis` | `idx_rfis_custody(workspace_id, custody_status)` | Custody-based queue filtering |
| `corrections` | `idx_corrections_document_batch(document_id, status)` | Batch-scoped correction queries via document |

---

*End of V2.54 Annotation Layer Artifact Specification*
