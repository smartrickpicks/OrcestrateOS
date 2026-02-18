#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
OUT_DIR="${ROOT_DIR}/out/uat"
TS="$(date +"%Y%m%d_%H%M%S")"
OUT_FILE="${OUT_DIR}/v256_uat_results_${TS}.md"

mkdir -p "${OUT_DIR}"

cat <<'TEMPLATE' > "${OUT_FILE}"
# V2.56 UAT Results

**Date:** __DATE__
**Environment:** __ENV__
**Build/Version:** __BUILD__
**Dataset ID:** __DATASET__

---

## Runbook Results (Summary)

| Section | Status | Evidence |
|---|---|---|
| Setup & Sanity | ☐ PASS / ☐ FAIL | |
| Analyst Flow | ☐ PASS / ☐ FAIL | |
| Verifier Flow | ☐ PASS / ☐ FAIL | |
| Admin Flow | ☐ PASS / ☐ FAIL | |
| Audit & Export | ☐ PASS / ☐ FAIL | |

---

## Role Checklists

### Analyst
| # | Item | Expected | Status | Evidence |
|---|---|---|---|---|
| A-1 | Create patch draft | Draft saved, `draft` | ☐ | |
| A-2 | Submit patch | Status `awaiting_verifier` | ☐ | |
| A-3 | Create RFI | RFI exists, `open` | ☐ | |
| A-4 | Submit RFI | Status `awaiting_verifier` | ☐ | |
| A-5 | Block self-approval | 403/validation error | ☐ | |

### Verifier
| # | Item | Expected | Status | Evidence |
|---|---|---|---|---|
| V-1 | View analyst submissions | Queue includes analyst items | ☐ | |
| V-2 | Return patch | Status `returned_to_analyst` | ☐ | |
| V-3 | Approve patch | Status `verified` | ☐ | |
| V-4 | Return RFI | Status `returned_to_analyst` | ☐ | |
| V-5 | Approve RFI | Status `verified` | ☐ | |

### Admin
| # | Item | Expected | Status | Evidence |
|---|---|---|---|---|
| AD-1 | View all queue items | Full workspace visibility | ☐ | |
| AD-2 | Promote verified patch | Status `approved`/`promoted` | ☐ | |
| AD-3 | Reject verified patch | Status `rejected` | ☐ | |
| AD-4 | Audit export | File includes custody events | ☐ | |

---

## Edge-Case Matrix

| ID | Scenario | Expected Result | Status | Notes |
|---|---|---|---|---|
| E-1 | Empty dataset | UI empty-state, no errors | ☐ | |
| E-2 | Unauthorized user | 401/403 | ☐ | |
| E-3 | Non-member | 401/403, no data | ☐ | |
| E-4 | Role-switch mid-session | Queue rehydrates | ☐ | |
| E-5 | Concurrent updates | 409 stale version | ☐ | |
| E-6 | Invalid transition | 409 INVALID_TRANSITION | ☐ | |
| E-7 | Network error on submit | No optimistic local write | ☐ | |

---

## Signoff

| Role | Name | Date | Decision | Notes |
|---|---|---|---|---|
| Analyst |  |  | ☐ PASS / ☐ FAIL |  |
| Verifier |  |  | ☐ PASS / ☐ FAIL |  |
| Admin |  |  | ☐ PASS / ☐ FAIL |  |
| QA Lead |  |  | ☐ GO / ☐ NO-GO |  |
| Product |  |  | ☐ GO / ☐ NO-GO |  |

TEMPLATE

# Replace placeholders to make the file immediately usable.
# Using sed for portability without GNU extensions.
DATE_VAL="$(date +"%Y-%m-%d")"
sed -i '' "s/__DATE__/${DATE_VAL}/g" "${OUT_FILE}"

cat <<EOF
Created: ${OUT_FILE}
