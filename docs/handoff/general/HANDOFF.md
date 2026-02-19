# HANDOFF (Governance Packet)

Audience: Verifiers and operators
Purpose: Provide a consistent packet for review and continuation
Scope: Docs and governance contracts only
Non-Goals: No code changes, no runtime actions, no PR merges
Authority Level: Informational, defers to canonical docs
Owner Agent: Documentation architect (Orchestrate OS)
Update Rules: Reference commits/PRs; otherwise use "Open — needs decision" with owner and evidence source

Repository: Orchestrate OS (formerly smartrickpicks/kiwi-semantic-control), branch: main
Open PRs: none known

## Current UI/UX Work In Progress
- Contract Health Score engine (P1G), Data Quality Check modal, Grid Mode, Pre-Flight intake (P1F.1), ADDRESS_INCOMPLETE_CANDIDATE matching — see replit.md § External Dependencies for full feature inventory

## Packet Contents
- STATUS.md — current snapshot
- TASKS.md — task backlog with evidence links
- TASKS_UI.md — UI-specific task backlog
- AUDIT.md — latest audit notes and diffs

## Known Risks/Regressions (docs-only)
- "Queue" appears in internal schema (Queue Item Schema, Verifier Queue, Admin Queue) while listed as a forbidden user-facing label — see Constraints below for clarification
- Some legacy/deprecated docs (load_data_view.md, V1/Flow-Doctrine.md) retain old terminology by design; deprecation headers are in place

## Constraints / Do-Not-Change List
- **Canonical terminology only**: Data Source, All Data Grid, Record Inspection, Verifier Review, Admin Approval; Review States; Submit Patch Request; Evidence Pack blocks (Observation, Expected, Justification, Repro)
- **Forbidden in user-facing UI labels**: Load Data, Apply Patch, Reviewer Hub
- **"Queue" clarification**: "Queue" is forbidden as a user-facing navigation/button label (use "Review States" or "Triage" instead). Internal schema terms (Queue Item Schema, Verifier Queue, Admin Queue) are permitted in technical docs and data contracts.
- **Note**: "Record Inspection" is the user-facing label; canonical internal token remains `single_row_review` in code/specs/audit

## Files Likely to Touch
- docs/ui/views/single_row_review_view.md
- docs/ui/gate_view_mapping.md
- docs/ui/ui_principles.md

---

## Shared PatchRequest Store (v1.5.2)

The `PATCH_REQUEST_STORE` provides cross-role access to PatchRequest objects.

### Storage Key Format
```
pr:{request_id}
```

### Lifecycle
| Action | Creates/Updates |
|--------|-----------------|
| Analyst submits patch | Creates new PatchRequest |
| Analyst responds to clarification | Updates existing PatchRequest |
| Verifier requests clarification | Updates status only |

### Usage
- **Analyst**: Creates PatchRequest on submit, stores in `PATCH_REQUEST_STORE`
- **Verifier**: Loads PatchRequest by `patch_request_id` from store
- **Admin**: Loads PatchRequest by `patch_request_id` from store

### Single Source of Truth
The shared store ensures Verifier/Admin views hydrate the exact PatchRequest created by the Analyst, including:
- `proposed_changes[]`
- `evidence_pack`
- `thread[]`
- `record_id`, `dataset_id`, `tenant_id`, `division_id`

---

## Queue Item Schema (v1.5.2)

Queue items route patches between roles. All fields are required.

### Required Fields

| Field | Type | Description |
|-------|------|-------------|
| `queue_item_id` | string | Unique queue entry ID |
| `dataset_id` | string | Source dataset identifier |
| `record_id` | string | Stable record identifier (hash-based) |
| `patch_request_id` | string | Reference to PATCH_REQUEST_STORE |
| `division_id` | string | Organizational division |
| `role` | string | Target role: `verifier`, `admin` |
| `assigned_to_user_id` | string | Assigned actor (or empty) |
| `status` | string | `pending_review`, `needs_clarification`, `sent_to_admin`, `resolved` |
| `created_at` | ISO 8601 | Queue entry timestamp |

### Queue Types
- **Verifier Queue**: Patches awaiting verifier review
- **Admin Queue**: Patches awaiting admin approval (after verifier approval)

---

## References
- docs/INDEX.md
- docs/overview.md
- docs/TRUTH_SNAPSHOT.md
- docs/handoff/srr-handoff-status.md
