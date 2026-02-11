# Stream Semantics Model

## Overview

This document describes the conceptual streaming model for continuous data processing in Orchestrate OS (formerly Kiwi Semantic Control Board). This is a **governance-only** explanation of how a future continuous pipeline would work - no actual runtime execution is implemented.

## Never-Stop Flow (Open Faucet Model)

In a continuous pipeline, records flow like water through an open faucet:

- **Good records** (CONSOLIDATED) pass through immediately
- **Partial records** wait in a holding area until missing data arrives in later sessions
- **Blocked records** require manual intervention before proceeding

This model prevents backlogs: instead of stopping the entire pipeline for one problem, issues are isolated and resolved asynchronously while the rest of the data flows through.

## Record State Model

Records are assigned one of four deterministic states based on their issues and actions:

| State | Condition | Flow Behavior |
|-------|-----------|---------------|
| **CONSOLIDATED** | No blocking or warning issues | Passes through immediately |
| **PARTIAL** | Has warning-level issues only | Usable but flagged for completion |
| **WAITING** | Has missing data warnings | Held until data arrives in later session |
| **BLOCKED** | Has blocking-level issues | Requires manual operator intervention |

### State Derivation Rules

States are derived deterministically from the issues attached to each record:

```
IF hasBlockingIssues THEN BLOCKED
ELSE IF hasMissingDataWarning THEN WAITING
ELSE IF hasWarningIssues THEN PARTIAL
ELSE CONSOLIDATED
```

## Session Model

A **session** represents a single ingest wave - a batch of records arriving at a point in time.

### Session Properties

| Property | Description |
|----------|-------------|
| `session_index` | Ordered sequence number (1, 2, 3, ...) |
| `timestamp` | Relative time marker (T+0, T+30min, T+60min, ...) |
| `records` | Count of records in this session |
| `states` | Distribution of states (CONSOLIDATED, PARTIAL, WAITING, BLOCKED) |
| `reconsolidated` | Count of records upgraded from previous sessions |

### Session Sorting

Sessions are sorted deterministically:
1. `session_index` ascending
2. Within session: `record_state` order (CONSOLIDATED > PARTIAL > WAITING > BLOCKED)
3. Within state: `severity` order (blocking > warning > info)
4. Within severity: join triplet ascending (nulls last)

## Reconsolidation Rules

Records can transition between states as new data arrives:

| Current State | Condition | New State | Action |
|---------------|-----------|-----------|--------|
| PARTIAL | All warnings resolved in later session | CONSOLIDATED | Release to downstream |
| WAITING | Missing data arrives | PARTIAL or CONSOLIDATED | Re-evaluate with new data |
| BLOCKED | Manual intervention + re-submit | CONSOLIDATED | Operator action required |
| CONSOLIDATED | New blocking issue detected | BLOCKED | Hold and notify |

## Flow Visualization

```
  ┌─────────┐     ┌──────────┐     ┌──────────────┐
  │ Ingest  │ ──► │ Validate │ ──► │ CONSOLIDATED │ ──► Downstream
  └─────────┘     └──────────┘     └──────────────┘
                       │
                       ▼
                 ┌──────────┐     ┌───────────────┐
                 │ Holding  │ ──► │ Reconsolidate │ ──► (re-evaluate)
                 └──────────┘     └───────────────┘
                 (PARTIAL/WAITING)
```

## Key Benefits

1. **No Backlogs**: Problems don't stop the entire pipeline
2. **Async Resolution**: Issues are resolved in parallel with normal flow
3. **Deterministic States**: State transitions are rule-based and auditable
4. **Visibility**: Operators can see exactly where records are in the flow

## UI Features (v0.9)

The viewer provides:

1. **Session Timeline Panel**: Visualizes sessions as ordered ingest waves
2. **Record State Summary**: Shows distribution of current states
3. **Flow Diagram**: Visual representation of the never-stop flow
4. **Reconsolidation Rules Table**: Reference for state transitions
5. **Copy Stream Semantics Markdown**: One-click export for PR documentation

## Non-Goals

This is a **conceptual model only**:

- No actual streaming or async processing
- No queues, workers, or APIs
- No changes to harness behavior
- No runtime execution of any kind

The model exists purely for governance documentation and operator understanding.

## Related Documents

- [CONTROL_BOARD_ARCHITECTURE.md](./CONTROL_BOARD_ARCHITECTURE.md)
- [RULE_LIFECYCLE.md](./RULE_LIFECYCLE.md)
- [TRUTH_SNAPSHOT.md](./TRUTH_SNAPSHOT.md)
