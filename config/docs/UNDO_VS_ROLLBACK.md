# Undo vs Rollback — V2.2 P1

## Overview

Orchestrate OS provides two distinct mechanisms for reversing changes: **Local Undo** (short-lived, session-scoped) and **Governed Rollback** (auditable, artifact-based). These serve different purposes and have different governance implications.

## Local Undo (`UndoManager`)

### Purpose
Quick reversal of draft-only edits made in Record Inspection or Patch Studio during the current session.

### Behavior
- **Window-based**: Entries expire after 5 minutes (300,000 ms)
- **Buffer limit**: Maximum 50 entries (oldest evicted first)
- **Session-only**: Buffer is in memory; cleared on page reload
- **Draft-only**: Cannot undo edits on artifacts with status `Submitted`, `Verifier_Approved`, `Admin_Approved`, or `Applied`
- **Append-only audit**: Emits `undo_local` event; never deletes history

### Audit Event: `undo_local`
```json
{
  "event_type": "undo_local",
  "record_id": "<sheet>:<row_index>",
  "field_key": "field_name",
  "before_value": "<value after the edit that was undone>",
  "after_value": "<restored original value>",
  "metadata": {
    "undo_id": "undo_xxx",
    "source": "srr_inline",
    "elapsed_ms": 12345
  }
}
```

### Usage
- Called via `srrUndoLastEdit()` from SRR interface
- Automatically pushed when `FIELD_CORRECTED` is emitted during inline editing

## Governed Rollback (`RollbackEngine`)

### Purpose
Formal, auditable reversal of applied changes at any scope level. Creates a rollback artifact that references the original event/artifact and applies state changes through an append-only mechanism.

### Scopes
| Scope | Function | Description |
|-------|----------|-------------|
| `field` | `createFieldRollback(recordId, fieldKey, beforeValue, reason, originalEventId)` | Reverts a single field to its prior value |
| `patch` | `createPatchRollback(patchRequestId, reason)` | Reverts all fields touched by a patch request |
| `contract` | `createContractRollback(contractId, reason)` | Snapshots and reverts all rows under a contract |
| `batch` | `createBatchRollback(reason)` | Snapshots and reverts all rows in the current batch |

### Two-Phase Flow
1. **Create** (`rollback_created`): Captures the rollback artifact with before-state snapshot and references to the original event/artifact. Does NOT apply any changes.
2. **Apply** (`rollback_applied`): Writes the before-state snapshot back to the workbook. This is an append-only operation — the current state is captured as `after_state` before overwriting.

### Key Properties
- **Never deletes history**: All rollback operations are additive
- **References original**: Each artifact stores `original_event_id` and/or `original_artifact_id`
- **Hinge-aware**: If rollback affects hinge fields, automatically triggers `SystemPass.run('rollback_hinge_affected')`
- **Auditable**: Both creation and application emit distinct audit events

### Audit Events

#### `rollback_created`
```json
{
  "event_type": "rollback_created",
  "record_id": "<record_id>",
  "field_key": "<field_key or null>",
  "metadata": {
    "rollback_id": "rb_xxx",
    "scope": "field|patch|contract|batch",
    "original_event_id": "<event_id or null>",
    "original_artifact_id": "<artifact_id or null>",
    "reason": "description"
  }
}
```

#### `rollback_applied`
```json
{
  "event_type": "rollback_applied",
  "record_id": "<record_id>",
  "field_key": "<field_key or null>",
  "before_value": "<state before rollback (current)>",
  "after_value": "<state after rollback (restored)>",
  "metadata": {
    "rollback_id": "rb_xxx",
    "scope": "field|patch|contract|batch",
    "original_event_id": "<event_id or null>",
    "original_artifact_id": "<artifact_id or null>",
    "hinge_affected": true|false
  }
}
```

## Hinge-Governed System Change Application

### Problem
System Pass proposals that touch hinge fields cannot be directly accepted because hinge fields require the full patch lifecycle (review gates, approval chain).

### Flow
1. System Pass generates proposals including `is_hinge: true` flag
2. When analyst clicks "Route to Patch" on a hinge proposal:
   - A `system_suggested` patch artifact is auto-created in `PATCH_REQUEST_STORE`
   - Proposal status set to `routed_to_patch`
   - `system_change_routed_to_patch` audit event emitted
3. The patch artifact follows the standard lifecycle: Draft → Submitted → Verifier Review → Admin Approval → Applied
4. Non-hinge proposals can still be accepted/rejected directly

### Audit Event: `system_change_routed_to_patch`
```json
{
  "event_type": "system_change_routed_to_patch",
  "record_id": "<record_id>",
  "field_key": "<hinge_field_key>",
  "metadata": {
    "proposal_id": "sp_xxx",
    "patch_request_id": "PR_SYS_xxx",
    "rule_id": "qa_rule",
    "is_hinge": true
  }
}
```

## Rollback-Triggered System Pass Rerun

When a rollback is applied and it affects one or more hinge fields:
1. `RollbackEngine.applyRollback()` detects the hinge field modification
2. Automatically calls `SystemPass.run('rollback_hinge_affected')`
3. New proposals are generated and rendered in the System Changes triage bucket
4. Toast notification informs the user of the auto-rerun and proposal count

## V2.2 P2 Polish

- **System Changes UX**: Bulk reject with reason, confidence sort/filter presets, hinge-required badge. System Pass proposals surface in the System Changes triage bucket with clear accept/reject/route actions.
- **Pre-Flight integration**: One-click "Create Patch from Blocker" creates governed `preflight_resolution` artifacts. Blocker types include unknown columns, OCR unreadable, low-confidence extraction, and mojibake.
- **Audit filter presets**: Saved locally, quick chips for system_change/rollback/schema_change/session. Presets persist across sessions via localStorage.
- **Export stability**: Audit-only export uses stable column ordering (event_id, timestamp, event_type, subtype, actor_role, scope_type, scope_id, payload_summary, artifact_refs). Column order is deterministic and version-pinned.

## Comparison Table

| Aspect | Local Undo | Governed Rollback |
|--------|-----------|-------------------|
| Scope | Single field edit | Field / Patch / Contract / Batch |
| Persistence | In-memory (session only) | Artifact-based (AuditTimeline) |
| Time window | 5 minutes | Unlimited |
| Artifact created | No | Yes (rollback artifact) |
| History preserved | Yes (audit event) | Yes (before/after snapshots) |
| Can touch approved artifacts | No | Yes (creates new state) |
| Hinge-aware | No | Yes (auto-triggers System Pass) |
| Audit event | `undo_local` | `rollback_created` + `rollback_applied` |

## Audit UI Integration

All undo and rollback events appear in:
- **Header dropdown**: Last 10 events (real-time badge counter)
- **Full audit panel**: Filterable under "Undo / Rollback" type category
- **Audit-only XLSX export**: Included with full schema (event_id, timestamp, actor_role, scope_type, scope_id, event_type, subtype, payload_summary, artifact_refs)
