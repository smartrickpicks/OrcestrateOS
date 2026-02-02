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

## Completed

| ID | Task | Evidence | Completed Date |
|----|------|----------|----------------|
| (none yet) | | | |

## References

- [STATUS.md](STATUS.md) — Current implementation state
- [TASKS.md](TASKS.md) — General task backlog
- [Human-Agent-Workflow-V1.json](../specs/Human-Agent-Workflow-V1.json) — Canonical node/edge definitions
- [NOMENCLATURE.md](../V1/NOMENCLATURE.md) — Term registry
