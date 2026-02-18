# V2.3 Release Checklist

## Pre-Flight Checklist

| # | Item | Status | Verified By | Date |
|---|------|--------|-------------|------|
| 1 | All G1–G9 gate logs emit PASS on demo dataset load | ☐ | | |
| 2 | All G1–G9 gate logs emit PASS on XLSX upload | ☐ | | |
| 3 | Smoke test passes (`scripts/replit_smoke.sh`) | ☐ | | |
| 4 | No JS errors on initial page load (DevTools Console) | ☐ | | |
| 5 | localStorage contains no dataset/workbook blobs (Application tab) | ☐ | | |
| 6 | IndexedDB `orchestrate_session` contains workbook after upload | ☐ | | |
| 7 | Decision memos complete and cross-referenced (`docs/memos/INDEX.md`) | ☐ | | |
| 8 | Gate verification runbook executed (`docs/V23_GATE_VERIFICATION_RUNBOOK.md`) | ☐ | | |

## Regression Checklist

| # | Item | Expected Behavior | Status | Notes |
|---|------|-------------------|--------|-------|
| 1 | Grid row click → Record Inspection | Clicking any row in All Data Grid opens Record Inspection for that record | ☐ | Guard: `[T0:GUARD] openRowReviewDrawer` |
| 2 | Record Inspection prev/next navigation | Prev/Next buttons navigate between records within the current contract section | ☐ | Guards: `[T0:GUARD] srrNavigatePrev`, `srrNavigateNext` |
| 3 | Triage grid structure | Triage page renders 4-queue layout (Pre-Flight, Semantic, Patch Review, System) | ☐ | |
| 4 | Contract section filter in grid | Changing contract section filter re-renders grid with correct contract section data | ☐ | Guard: `[T0:GUARD] renderGrid` |
| 5 | Contract selector stable | Contract count badge unchanged when switching contract sections | ☐ | G7 verified |
| 6 | Patch Studio submit | Patch can be drafted and submitted from Record Inspection | ☐ | |
| 7 | Verifier approval flow | Verifier can approve submitted patch (not self-authored) | ☐ | |
| 8 | Admin promotion flow | Admin can approve and promote verified patch | ☐ | |
| 9 | Audit timeline renders | Audit panel shows events with filtering and export | ☐ | |
| 10 | PDF viewer opens | Clicking PDF link opens viewer with document | ☐ | |

## Ship / No-Ship Signoff

| Role | Decision | Name | Date | Notes |
|------|----------|------|------|-------|
| Engineering | ☐ Ship / ☐ No-Ship | | | |
| QA | ☐ Ship / ☐ No-Ship | | | |
| Product | ☐ Ship / ☐ No-Ship | | | |

### No-Ship Criteria (any = No-Ship)
- Any G1–G9 gate emits FAIL
- Regression checklist item fails
- JS errors on page load
- localStorage contains dataset blobs
- Smoke test fails
