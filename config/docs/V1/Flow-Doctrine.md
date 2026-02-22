# Flow Doctrine (V1)

> Human authority governs all semantic decisions. Agents assist; they do not autonomously apply changes.

## Purpose

This document defines the governance workflow for human+agent collaboration in the Orchestrate OS control plane. It ensures:

- **Determinism**: Same inputs produce identical outputs
- **Auditability**: Every decision has traceable evidence
- **Human Authority**: Operators approve or reject; agents propose
- **Offline-First**: No network dependencies for validation

## Workflow Stages

### Stage 1: Load Data
- **Actor**: Operator
- **Action**: Load dataset (sample, CSV, or attached file)
- **Gate**: Dataset must parse without errors
- **Evidence**: Row count, column headers, parse timestamp

### Stage 2: Triage Review
- **Actor**: Operator
- **Action**: Review Review State counts and summary cards
- **Gate**: Operator acknowledges data state
- **Evidence**: Review State snapshot (To Do, Needs Review, Flagged, Blocked, Finalized)

### Stage 3: Record Inspection
- **Actor**: Operator
- **Action**: Drill into individual records, examine field values
- **Gate**: Record selected and visible
- **Evidence**: Record ID, field values, current status

### Stage 4: Issue Identification
- **Actor**: Operator (with optional agent suggestion)
- **Action**: Identify semantic issue or rule gap
- **Gate**: Issue articulated in plain language
- **Evidence**: Observation statement, expected behavior

### Stage 5: Patch Draft Authoring (Patch Studio)
- **Actor**: Operator
- **Action**: Author Evidence Pack using structured intent (WHEN→Observation / THEN→Expected / BECAUSE→Justification)
- **Gate**: All required fields populated
- **Evidence**: Intent preview, target field, condition, action

### Stage 6: Preflight Check
- **Actor**: System (automated)
- **Action**: Validate patch structure and dependencies
- **Gate**: All preflight checks pass or warn (no fail)
- **Evidence**: Preflight report with pass/warn/fail badges

### Stage 7: Evidence Pack Assembly
- **Actor**: Operator
- **Action**: Complete 4-block Evidence Pack
- **Gate**: All 4 canonical blocks populated:
  - **Observation** (alias: WHEN)
  - **Expected** (alias: THEN)
  - **Justification** (alias: BECAUSE)
  - **Repro** (no alias)
- **Evidence**: Timestamped Evidence Pack snapshot

### Stage 8: Submit Patch Request
- **Actor**: Operator
- **Action**: Submit Patch Request for review
- **Gate**: Submission logged
- **Evidence**: Audit log entry with timestamp and actor

### Stage 9: Verifier Review
- **Actor**: Verifier (elevated role)
- **Action**: Review Patch Request, request clarification or approve/reject
- **Gate**: Verifier decision recorded
- **Evidence**: Review notes, decision status, revision history

### Stage 10: Admin Approval
- **Actor**: Admin (elevated role)
- **Action**: Final approval of Patch Request, hold, or export to external system
- **Gate**: Admin decision recorded; Patch Request becomes Approved Patch
- **Evidence**: Admin action log, export payload if applicable

### Stage 11: Promote Patch to Baseline
- **Actor**: Admin (after external confirmation if required)
- **Action**: Promote Approved Patch to semantic baseline; patch becomes Baseline Patch
- **Gate**: Confirmation of promotion
- **Evidence**: Promotion timestamp, baseline version updated

### Stage 12: Export (PR Ready)
- **Actor**: Operator or Admin
- **Action**: Export Baseline Patch artifacts for pull request
- **Gate**: All Baseline Patches included
- **Evidence**: Patch file, changelog entry, Smoke (Strict) pass

## Authority Model

| Role | Can Author | Can Review | Can Approve | Can Export |
|------|-----------|-----------|-------------|------------|
| Analyst | Yes | No | No | No |
| Verifier | Yes | Yes | No | No |
| Admin | Yes | Yes | Yes | Yes |

## Drift Detection

Deprecated terms that indicate drift from V1 naming:
- "Kiwi Control Board" → use "Semantic Control Board"
- "All-Data Grid" → use "All Data Grid" (no hyphen)
- "Reviewer Hub" → use "Verifier Review"
- "Queue" as standalone nav label → use specific Review State name

## Acceptance Tests

1. **Load Test**: Sample dataset loads with correct row count
2. **Triage Test**: Review State counts match data state
3. **Patch Test**: Structured intent renders correctly
4. **Preflight Test**: Invalid patches show fail badge
5. **Submit Test**: Audit log captures submission
6. **Review Test**: Verifier actions update status correctly
7. **Export Test**: Applied patches export to valid patch file

## Related Documents

- [Human-Agent-Workflow-V1.json](../specs/Human-Agent-Workflow-V1.json) — Machine-readable workflow spec
- [Miro Diagram Prompt](../assets/miro/Human-Agent-Workflow-MiroPrompt.txt) — Visual diagram generation
- [INDEX.md](../INDEX.md) — Full documentation index
