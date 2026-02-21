# AUDIT_LOG — Offline, Append-Only Evidence Ledger

Contract: This document defines the governance contract for the read-only audit and evidence log used by Orchestrate OS (Semantic Control Board). It specifies event types, deterministic schema, ordering, and UI rendering requirements. It does not describe implementation code, services, or runtime hooks.

## Scope
- Read-only, append-only ledger of human-governed events and attached evidence.
- Offline-first: all entries are materialized through human action and stored within repository-bound assets.
- Deterministic: schema, ordering, and normalization are fully specified to enable reproducible views and verifiable digests.
- Governance-only: navigation surfaces never mutate state; only governed views can own gates and author gate events.

## Non-Goals
- No runtime webhooks, background listeners, or mutation endpoints.
- No implicit transitions or auto-review.
- No external identity or transport guarantees beyond what is recorded in the ledger.

## Core Principles
- Append-only: past entries are never edited; corrections are represented as new events that reference prior entries.
- Human authority: all semantic decisions (e.g., patches, state marks) are attributed to a role and actor and must cite evidence.
- Determinism: canonical field order, value normalization, and sort rules are defined and must be followed.
- Evidence first: every consequential decision should link to concrete anchors (e.g., PDF highlights) and be replayable in the UI.


## Implementation (v1.6.59)

### Storage
All audit events are persisted in an IndexedDB database (`orchestrate_audit`) with an `events` object store. Events are also held in a memory cache for synchronous access during export. IndexedDB indexes enable efficient queries by `dataset_id`, `file_id`, `record_id`, `event_type`, `actor_role`, and compound `[dataset_id, file_id]`.

### Event Schema (v1.6.59)
| Field | Type | Description |
|-------|------|-------------|
| event_id | string | Unique identifier (format: `evt_{timestamp_base36}_{random}`) |
| event_type | string | One of the event types below |
| actor_id | string | Email or name of the acting user |
| actor_role | string | One of: analyst, verifier, admin |
| timestamp_iso | string | ISO-8601 UTC timestamp |
| dataset_id | string | Active dataset identifier |
| file_id | string | File name or sheet name |
| record_id | string | Record key (sheet:index or stable hash) |
| field_key | string (nullable) | Specific field affected |
| patch_request_id | string (nullable) | Related patch request ID |
| before_value | string (nullable) | Value before change |
| after_value | string (nullable) | Value after change |
| metadata | object | Event-specific details (status transitions, decisions, etc.) |

### Event Coverage (v1.6.59)
| Event Type | Emitted By | Description |
|------------|-----------|-------------|
| PATCH_SUBMITTED | srrSubmitPatchRequest | Analyst submits a patch request from Record Inspection |
| PATCH_REQUEST_SUBMITTED | updatePatchRequestStatus | Patch enters Submitted status |
| VERIFIER_APPROVED | updatePatchRequestStatus | Verifier approves patch |
| ADMIN_APPROVED | updatePatchRequestStatus | Admin approves patch |
| PATCH_ADMIN_PROMOTED | aaAdminApprove | Admin promotes patch (final approval) |
| PATCH_REJECTED | updatePatchRequestStatus | Verifier or Admin rejects patch |
| PATCH_CANCELLED | updatePatchRequestStatus | Patch cancelled |
| CLARIFICATION_REQUESTED | updatePatchRequestStatus | Verifier requests clarification |
| CLARIFICATION_RESPONDED | updatePatchRequestStatus | Analyst responds to clarification |
| REQUEST_CLARIFICATION | verifierRequestClarification | Field-level clarification request |
| FIELD_VERIFIED | srrVerifyField, verifierApproveField | Field marked as verified |
| FIELD_BLACKLISTED | srrBlacklistField | Field flagged for blacklist |
| FIELD_CORRECTED | verifierRejectField | Verifier rejects a field |
| MANUAL_ROW_ADD | batchAddRows | Rows added via batch add |
| CATALOG_GROUP_SET | markAsGroupAnchor | Record set as Catalog Item Anchor (enum key preserved for backward compatibility; UI label is "Catalog Item Anchor") |
| SESSION_RESTORED | session restore | Session restored from IndexedDB cache |
| SYSTEM_CHANGE_APPLIED | aaShowReplayAuditLog | Replay evaluation result |
| ADMIN_HOLD_SET | updatePatchRequestStatus | Admin places hold |
| ADMIN_HOLD_RELEASED | updatePatchRequestStatus | Admin releases hold |
| SENT_TO_KIWI | updatePatchRequestStatus | Patch sent to external system |
| KIWI_RETURN_INGESTED | updatePatchRequestStatus | External system response ingested |
| PATCH_APPLIED | updatePatchRequestStatus | Patch applied to dataset |
| CONTRACT_INDEX_BUILT | ContractIndex.build | Contract index built after workbook population (v2.2 P0) |
| CONTRACT_ROLLUP_UPDATED | openContractDetailDrawer | Contract rollup viewed with aggregate counts (v2.2 P0) |
| UNKNOWN_COLUMN_DETECTED | ContractIndex._routeUnknownColumns | Unknown column detected in contract section (v2.2 P0) |
| BATCH_CREATED | ContractIndex.build | Batch created from workbook data (v2.2 P0) |
| SCHEMA_CHANGE | SchemaTreeEditor | Schema change with subtype: alias_patch, schema_patch, tenant_rule_patch, suppression_patch (v2.2 P1) |
| batch_merged | BatchMerge.executeMerge | Batches merged into governance container (v2.2 P2). Canonical name; legacy `BATCH_MERGED` alias-mapped at read time. Payload: merged_batch_id, source_batches, contracts, total_rows, documents, created_by |
| tenant_rule_promoted_to_batch | BatchMerge.promoteTenantRule | Tenant rule manually promoted to merged batch (v2.2 P2). Canonical name; legacy `TENANT_RULE_PROMOTED_TO_BATCH` alias-mapped. Payload: merged_batch_id, sheet, field, rule, promoted_by, total_promoted |
| system_change_routed_to_patch | SystemPass.acceptProposal (hinge) | Hinge proposal routed to patch lifecycle (v2.2 P1) |
| undo_local | UndoManager.undo | Local draft edit undone (session-scoped) (v2.2 P1) |
| rollback_created | RollbackEngine.createRollback | Rollback artifact created (not yet applied) (v2.2 P1) |
| rollback_applied | RollbackEngine.applyRollback | Rollback artifact applied (append-only) (v2.2 P1) |
| ROW_SANITIZED_HEADER_ECHO | parseWorkbook | Header-echo row removed at parse time when token overlap >= 60% (v2.3). Payload: sheet_name, row_index, match_ratio |
| preflight_blocker_detected | _governedDecisions triage | Pre-Flight blocker detected (v2.3 updated). Payload: record_id, field_key, metadata.blocker_type, metadata.sheet, metadata.non_empty, metadata.scope. Severity computed from rollup: >0 warning, >3 blocker |
| patch_from_preflight_blocker | createPatchFromBlocker | Patch created from Pre-Flight blocker (v2.2 P2) |

### No Synthetic Events
All timeline entries are built exclusively from persisted events. No placeholder or demo rows are generated at render time.

### Export (v1.6.59)
The `Audit_Log` sheet is included in exported XLSX workbooks. It contains all events for the active dataset with columns in the stable order defined above. Events are sorted by `timestamp_iso` ascending.

## PDF Cache Index Contract (v1.4.13)

The PDF cache is a local UI concern and does not emit governance events. However, the cache index schema is documented for tooling interoperability:

### Cache Index Entry Fields
| Field | Type | Description |
|-------|------|-------------|
| key | string | Cache key: `pdf:{record_id}:{source_url_without_query}` |
| source_url | string | Original network URL |
| size_bytes | integer | File size in bytes |
| created_at | integer | Unix timestamp (ms) when cached |
| last_accessed_at | integer | Unix timestamp (ms) of last access |

### Cache Limits
| Limit | Value |
|-------|-------|
| MAX_FILE_BYTES | 25 MB (26,214,400 bytes) |
| MAX_TOTAL_BYTES | 250 MB (262,144,000 bytes) |

### Cache Operations
Cache operations are local UI concerns and are NOT logged to the audit ledger:
- Cache writes, reads, and evictions are silent
- Only explicit governance actions (PATCH_*, STATE_MARKED, etc.) are logged
- The cache exists purely for offline convenience and has no semantic authority

## Event Model
Each entry in the audit log is an Event with the following invariant fields:
- event_id: globally unique stable identifier (string). Example: ULID or UUIDv4 rendered lowercase.
- event_seq: monotonically increasing integer scoped to the `record_id`. Starts at 1 with the first event for a record; gaps are not reused.
- occurred_at: UTC timestamp in ISO-8601 with Z suffix. Example: 2026-02-01T12:34:56Z
- captured_at: UTC timestamp in ISO-8601 with Z suffix documenting when the event was recorded into the ledger.
- record_id: stable identifier of the governed record (string).
- dataset_id: stable identifier of the dataset containing the record (string). Optional for cross-cutting events.
- patch_id: identifier of the patch when present (string, optional).
- actor.handle: free-form actor label (string, may be pseudonymous or local handle).
- actor.role: one of [Analyst, Verifier, Admin].
- view: originating view (string). Examples: data_source_view, single_row_review_view, verifier_review_view, admin_approval_view.
- event_type: see Event Types below (string enum).
- payload: event-specific, deterministic object (see Payload Contracts).
- evidence: zero or more evidence anchors (array; see Evidence Anchors).

### Event Types

#### Ingestion Events
- INGESTION_REGISTERED: a file was accepted into the inbound folder with checksum recorded. Origin: data_source_view.
- SUBMISSION_ATTRIBUTED: submitter identity was resolved for an ingested file. Origin: data_source_view.
- ROUTED_TO_ANALYST: a record was assigned an initial Review State after ingestion. Origin: data_source_view.
- OUTPUT_PUBLISHED: finalized output was written to the outbound folder. Origin: admin_approval_view.

#### Core Events
- LOADED: data was loaded into the system through the governed loader (copy-only ingestion). Origin: data_source_view.
- VIEWED: a record was opened in a governed inspection view. Origin: any read-only view.
- PATCH_DRAFTED: an Analyst authored an initial Patch Draft (no submission yet). Origin: single_row_review_view (Evidence Pack panel).
- PATCH_SUBMITTED: an Analyst submitted a Patch Request for verification. Origin: single_row_review_view. This does not change Review State.
- REVIEW_REQUESTED: explicit request for verification on a record or patch. Origin: single_row_review_view.
- NOTE_ADDED: a structured note or comment was added. Origin: any governed view.
- FLAG_ADDED: a flag was set with category and rationale. Origin: single_row_review_view or verifier_review_view.
- FLAG_CLEARED: a previously set flag was cleared with rationale. Origin: verifier_review_view or admin_approval_view.
- STATE_MARKED: review state was marked to a target state by a governed gate. Origin: verifier_review_view or admin_approval_view only.
- EVIDENCE_ATTACHED: evidence anchors were added to an existing entry or patch. Origin: single_row_review_view or verifier_review_view.
- EXPORT_GENERATED: a deterministic export or snapshot was generated. Origin: single_row_review_view or admin_approval_view.

#### Replay Events (v1.4.17)
- REPLAY_EVALUATED: Patch Replay gate was executed. Origin: admin_approval_view.
- REPLAY_PASSED: Patch Replay completed successfully (all checks passed). Origin: admin_approval_view.
- REPLAY_FAILED: Patch Replay failed one or more checks. Origin: admin_approval_view.

Review States (for STATE_MARKED): one of [To Do, Needs Review, Flagged, Blocked, Finalized].

## Deterministic Event Schema (Canonical Order)
Field order is fixed for canonical serialization and hashing:
1. event_id (string)
2. event_seq (integer)
3. occurred_at (ISO-8601 UTC Z)
4. captured_at (ISO-8601 UTC Z)
5. record_id (string)
6. dataset_id (string | null)
7. patch_id (string | null)
8. actor.handle (string)
9. actor.role (Analyst | Verifier | Admin)
10. view (string)
11. event_type (enum)
12. payload (object; see below)
13. evidence (array of Evidence Anchors)

Normalization rules:
- Strings are trimmed; internal whitespace normalized to single spaces where applicable.
- Enums are case-sensitive and must match exactly.
- Arrays are ordered as specified (e.g., `changes` in a patch must be stable-sorted by `path`).
- Null values are explicit; omitted fields are not allowed.

## Payload Contracts (by event_type)

### Ingestion Event Payloads

INGESTION_REGISTERED payload fields (canonical order):
- file_path (string; repository-relative path, e.g., "inbound/contracts.xlsx")
- checksum_sha256 (string; 64-char hex digest)
- file_size_bytes (integer)
- detected_type (string; csv | xlsx | json | pdf)

SUBMISSION_ATTRIBUTED payload fields:
- file_path (string; repository-relative path)
- submitter (string; email or identifier)
- attribution_method (string; folder_name | manifest | auth_token)

ROUTED_TO_ANALYST payload fields:
- record_id (string)
- source_file (string; repository-relative path)
- initial_review_state (string; typically "To Do")
- assigned_pool (string; "analyst")

OUTPUT_PUBLISHED payload fields:
- output_path (string; repository-relative path, e.g., "outbound/2026-02-02_140000/sf_packet.json")
- record_count (integer)
- approved_by (string; admin identifier)

### Core Event Payloads

LOADED payload fields (canonical order):
- file_path (string; repository-relative path)
- file_format (string; csv | xlsx)
- sheet_name (string | null; xlsx only)
- row_count (integer)
- column_count (integer)
- headers (array of strings)
- source_checksum (string; hex digest of original file bytes)

VIEWED payload fields:
- context (string; e.g., "record", "patch", "audit")

PATCH_DRAFTED payload fields:
- patch_id (string)
- changes (array of change objects; stable-sorted by `path`)
  - For each change: path (JSON Pointer), before (scalar | object | array | null), after (scalar | object | array | null), rationale (string)

PATCH_SUBMITTED payload fields:
- patch_id (string)
- submission_notes (string)

REVIEW_REQUESTED payload fields:
- target (string; "record" | "patch")
- patch_id (string | null)
- reason (string)

NOTE_ADDED payload fields:
- category (string)
- text (string)

FLAG_ADDED payload fields:
- category (string)
- severity (string; info | warning | error | critical)
- rationale (string)

FLAG_CLEARED payload fields:
- category (string)
- rationale (string)

STATE_MARKED payload fields:
- from_state (enum; Review States)
- to_state (enum; Review States)
- gate_view (string; must be verifier_review_view or admin_approval_view)
- rationale (string)

EVIDENCE_ATTACHED payload fields:
- anchor_group_id (string)
- purpose (string)

EXPORT_GENERATED payload fields:
- export_path (string; repository-relative)
- export_format (string)
- rationale (string)

### Replay Event Payloads (v1.4.17)

REPLAY_EVALUATED payload fields:
- result (string; "pass" | "fail")
- checks (array of check objects)
  - For each check: id (string), pass (boolean)
- failure_reason (string | null)

REPLAY_PASSED payload fields:
- checks (array of check objects)
  - For each check: id (string), pass (boolean)
- evaluated_at (ISO-8601 UTC Z)

REPLAY_FAILED payload fields:
- checks (array of check objects)
  - For each check: id (string), pass (boolean)
- failure_reason (string)
- failed_check_id (string)
- evaluated_at (ISO-8601 UTC Z)

## Evidence Anchors
Each evidence entry is a deterministic anchor that the UI can resolve:
- anchor_id (string; unique within the record)
- doc_path (string; repository-relative path to source, e.g., a PDF)
- page_index (integer; zero-based)
- text_snippet (string; excerpt used to locate the highlight)
- bbox (array of 4 numbers; [x, y, w, h] in normalized page coordinates 0..1)
- selector (string; optional alternative selector like a hash of the snippet)

Evidence arrays are ordered by anchor_id ascending. All anchors must be resolvable offline.

## Ordering & Deterministic Digest
- Primary sort: event_seq ascending within a record.
- Tie-break: event_id lexicographic ascending (should not occur in practice).
- Canonical digest (for verification): SHA-256 over the canonical serialization (field order as above, UTF-8, LF newlines, normalized whitespace). The digest is not an event field in the schema; if stored, it must be placed in an external verification file.

## UI Rendering Requirements
- Presentation: vertical timeline grouped by record; event icon by type; badge for review state in STATE_MARKED entries.
- Filtering: by event_type, actor.role, view, review state transitions, presence of evidence. Saved filter presets are stored locally. Quick chips provide one-click filtering for common categories: system_change, rollback, schema_change, session.
- Evidence: each evidence anchor must be clickable to open the document viewer at the specified page and highlight the bbox. Opening evidence is read-only.
- Patch context: PATCH_* events must display the number of changes and allow expanding a read-only diff; no editing from the audit view.
- Gate provenance: STATE_MARKED events must display the gate_view value and rationale.
- No mutation controls: no approve, promote, or mark actions are available in the audit view.

## Review State Rules (for compatibility)
- Allowed states: To Do, Needs Review, Flagged, Blocked, Finalized.
- Navigation surfaces never perform state transitions.
- Only governed views (verifier_review_view, admin_approval_view) may emit STATE_MARKED.

## Redaction & Privacy
- Redactions are represented as new PATCH_* events; original entries remain intact.
- If a snippet contains sensitive text, the text_snippet may be replaced by a deterministic placeholder while preserving selector and bbox.

## Data Residency
- All file paths are repository-relative and must resolve under docs_root or designated data directories.
- No external URLs are required to render or verify the audit log.
