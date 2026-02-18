# Role: Analyst

> Default operator role for data loading, triage, record inspection, and patch authoring.

## Overview

The Analyst is the primary operator role responsible for:
- Loading and reviewing datasets
- Identifying issues in records
- Authoring patch requests with structured intent
- Assembling evidence packs for review

## Can / Cannot

### Can Do

| Capability | Description |
|------------|-------------|
| Open Data Source | Import CSV, load sample dataset, attach files |
| View Triage | See Review State counts and summary cards |
| Inspect Records | Drill into individual records, view field values |
| Author Patches | Create structured intent (WHEN/THEN/BECAUSE) |
| Run Preflight | Trigger preflight validation on draft patches |
| Assemble Evidence | Complete 4-block evidence pack |
| Submit Patch Request | Submit patch request for review |
| Respond to Clarification | Address verifier questions on own patches |

### Cannot Do

| Restriction | Reason |
|-------------|--------|
| Review patches authored by others | Requires Verifier role |
| Approve or reject patches | Requires Verifier or Admin role |
| Promote Patch to Baseline | Requires Admin role |
| Export to PR | Requires Admin role |
| Access Admin Console | Role-gated UI section |

## Allowed State Transitions

Based on the Review State Transition Matrix:

| From State | To State | Action |
|------------|----------|--------|
| Draft | Submitted | Submit Patch Request |
| Needs_Clarification | Submitted | Respond to Clarification |

## Gate Responsibilities

| Gate | Analyst Role |
|------|--------------|
| gate_parse | Owner — must load valid dataset |
| gate_preflight | Owner — must trigger and pass preflight |
| gate_evidence | Owner — must complete evidence pack |
| gate_verifier | Read-only — awaits verifier decision |
| gate_admin | No access |

## View Access

| View | Access Level |
|------|-------------|
| Triage | Full access |
| Record Inspection | Full access |
| Patch Authoring (Patch Studio) | Full access |
| Verifier Review | Read-only (own patches only) |
| Admin Approval | No access |
| Promotion | No access |

## Audit Requirements

Actions that must be logged:
- Dataset load (timestamp, row count, source)
- Patch submission (timestamp, patch_id, actor)
- Clarification response (timestamp, patch_id, revision_number)

## Related Documents

- [ui_principles.md](../ui_principles.md) — UI principles and transition matrix
- [Flow-Doctrine.md](../../V1/Flow-Doctrine.md) — Workflow stages
- [patch_authoring_view.md](../views/patch_authoring_view.md) — Patch Studio view contract
