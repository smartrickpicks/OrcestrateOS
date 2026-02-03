# TASKS_UI (Handoff — UI Backlog)

<!--
Audience: Governance reviewers and UI operators
Purpose: Track UI tasks with governance constraints and evidence links
Scope: UI copy and contracts only; no runtime or implementation claims
Non-Goals: No claims of completion without evidence (commit/PR URL)
Authority Level: Informational; defers to canonical docs
Owner Agent: Kiwi (documentation architect)
Update Rules: Each task must include scope, files likely to touch, and acceptance criteria
-->

## Overview

This document tracks UI-related tasks that have governance implications. Tasks here are proposals until evidence (commit hash or PR URL) confirms completion.

## Canonical Terminology

All tasks must use these terms exclusively:

| Canonical Term | Forbidden Alternatives |
|----------------|------------------------|
| Data Source | Load Data, Loader |
| All Data Grid | All-Data Grid |
| Single Row Review | Record Inspection |
| Patch Authoring | Patch Studio (for authoring phase) |
| Submit Patch Request | Submit to Queue |
| Verifier Review | Reviewer Hub |
| Admin Approval | Apply Patch (for approval phase) |
| Promote Patch | Apply Patch (for promotion phase) |
| Review State | Queue |
| Audit Log | (none) |

## Backlog

### IN PROGRESS

| ID | Task | Scope | Files Likely to Touch | Acceptance Criteria | Status |
|----|------|-------|----------------------|---------------------|--------|
| SRR-BUG-01 | BUGFIX: SRR row open uses active sheet selection (currentSheetFilter error) | UI bugfix | `ui/viewer/index.html` | No ReferenceError on row click; SRR_OPEN log shows sheetName != "unknown" | Done (9c4bfda) |
| SRR-BUG-02 | BUGFIX: Grid row click resolves correct sheet + record (no data row not found) | UI bugfix | `ui/viewer/index.html` | Click opens SRR without "data row not found"; console shows sheetName and recordIndex | In Progress |

### P1 — High Priority

| ID | Task | Scope | Files Likely to Touch | Acceptance Criteria | Status |
|----|------|-------|----------------------|---------------------|--------|
| UI-01 | Replace "Load Data" label with "Data Source" in sidebar nav | UI copy | `ui/viewer/index.html` | Sidebar shows "Data Source" | Pending |
| UI-02 | Replace "Record Inspection" references with "Single Row Review" | UI copy | `ui/viewer/index.html`, docs | All UI labels use "Single Row Review" | Pending |
| UI-03 | Update drawer title from "Load Data" to "Data Source" | UI copy | `ui/viewer/index.html` | Drawer header shows "Data Source" | Pending |

### P2 — Medium Priority

| ID | Task | Scope | Files Likely to Touch | Acceptance Criteria | Status |
|----|------|-------|----------------------|---------------------|--------|
| UI-04 | Audit all "Queue" references in UI copy | UI copy | `ui/viewer/index.html` | No standalone "Queue" labels; use Review State names | Pending |
| UI-05 | Ensure Patch Studio Submit button says "Submit Patch Request" | UI copy | `ui/viewer/index.html` | Button label is "Submit Patch Request" | Pending |

### P3 — Low Priority

| ID | Task | Scope | Files Likely to Touch | Acceptance Criteria | Status |
|----|------|-------|----------------------|---------------------|--------|
| UI-06 | Add deprecation tooltips for legacy terms (dev mode only) | UI behavior | `ui/viewer/index.html` | Dev mode shows tooltips on legacy terms | Pending |

### SRR — Single Row Review Enhancements (v1.4.1)

| ID | Task | Scope | Files Likely to Touch | Acceptance Criteria | Status |
|----|------|-------|----------------------|---------------------|--------|
| SRR-UI-01 | Field Cards + Groups/Filters in left panel | UI structure | `ui/viewer/index.html` | Left panel shows field cards (not simple list), 3+ groups exist in UI, edited fields visually differ from unchanged | Done |
| SRR-PATCH-01 | Inline edit auto-creates Proposed Change | UI behavior | `ui/viewer/index.html` | Editing any field adds Proposed Change with from/to, includes field label + api name, Edited chip appears immediately | Done |
| SRR-PATCH-02 | Mini patch prompt under edited field | UI behavior | `ui/viewer/index.html` | Mini patch prompt appears after edit with Justification/Comment inputs, Undo Change reverts to original | Done |
| SRR-GUARD-01 | Unsaved changes guard modal | UI behavior | `ui/viewer/index.html` | Back to Grid triggers modal when edits exist, Discard clears edits + proposed changes | Done |
| SRR-PATCH-03 | Patch Type category selector stub | UI behavior | `ui/viewer/index.html` | Each proposed change shows category (Correction/Blacklist Flag/RFI), category persists in session state | Done |

## Completed

| ID | Task | Evidence | Completed Date |
|----|------|----------|----------------|
| SRR-UI-01 | Field Cards + Groups/Filters | Commit TBD | 2026-02-03 |
| SRR-PATCH-01 | Inline edit auto-creates Proposed Change | Commit TBD | 2026-02-03 |
| SRR-PATCH-02 | Mini patch prompt under edited field | Commit TBD | 2026-02-03 |
| SRR-GUARD-01 | Unsaved changes guard modal | Commit TBD | 2026-02-03 |
| SRR-PATCH-03 | Patch Type category selector stub | Commit TBD | 2026-02-03 |

## References

- [STATUS.md](STATUS.md) — Current implementation state
- [TASKS.md](TASKS.md) — General task backlog
- [Human-Agent-Workflow-V1.json](../specs/Human-Agent-Workflow-V1.json) — Canonical node/edge definitions
- [NOMENCLATURE.md](../V1/NOMENCLATURE.md) — Term registry
