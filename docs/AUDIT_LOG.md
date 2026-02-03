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
- Filtering: by event_type, actor.role, view, review state transitions, presence of evidence.
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
