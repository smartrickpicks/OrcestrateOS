# V2.56 UAT Pack

**Version:** v2.56  
**Date:** 2026-02-18  
**Owner:** QA / Product  
**Status:** Draft for execution

---

## 1. Scope

This UAT pack validates end-to-end Analyst → Verifier → Admin flows, critical edge cases (empty/error/role-switch/concurrency), and captures a pass/fail signoff suitable for release readiness.

---

## 2. Preconditions

- Environment: Staging or UAT workspace with seeded data and 3 test users (Analyst, Verifier, Admin).
- Feature flags: Set per UAT environment runbook for v2.56.
- Dataset: Use the standard UAT dataset (or record the dataset ID and checksum).
- Evidence capture: Screenshots of key screens, API responses, audit log exports.

**Artifacts:**
- Runbook: This document §3–§6
- Pass/fail helper: `scripts/uat/v256_uat_pass_fail.sh` (writes a results template to `out/uat/`)

---

## 3. Runbook (Expected Outputs Included)

### 3.1 Setup & Sanity

| Step | Action | Expected Output |
|---|---|---|
| S1 | Login as Analyst | Dashboard loads; no console errors |
| S2 | Confirm workspace + dataset loaded | Dataset visible; record counts non-zero |
| S3 | Verify feature flags / build version | Version banner or build info matches v2.56 |
| S4 | Clear cache and re-login | Session rehydrates; no stale data warnings |

### 3.2 Analyst Flow (Create + Submit)

| Step | Action | Expected Output |
|---|---|---|
| A1 | Open a record in Record Inspection | Drawer opens with full record details |
| A2 | Create a patch draft | Draft saved; status = `draft` |
| A3 | Submit patch for verification | Status transitions to `awaiting_verifier`; audit event logged |
| A4 | Create an RFI | RFI created; status = `open` |
| A5 | Submit RFI to verifier | Status = `awaiting_verifier`; audit event logged |
| A6 | Attempt to approve own submission | Blocked; 403/validation error shown |

### 3.3 Verifier Flow (Review + Approve/Return)

| Step | Action | Expected Output |
|---|---|---|
| V1 | Login as Verifier | Verifier sees workspace-wide queue |
| V2 | Open Analyst patch | Patch details visible; author shown |
| V3 | Return patch to Analyst | Status = `returned_to_analyst`; audit event logged |
| V4 | Approve another patch | Status = `verified`; audit event logged |
| V5 | Return RFI to Analyst | Status = `returned_to_analyst`; audit event logged |
| V6 | Approve RFI | Status = `verified`; audit event logged |

### 3.4 Admin Flow (Promote + Finalize)

| Step | Action | Expected Output |
|---|---|---|
| AD1 | Login as Admin | Admin sees full queue + admin actions |
| AD2 | Promote verified patch | Status = `approved` (or `promoted`); audit event logged |
| AD3 | Reject a verified patch | Status = `rejected`; audit event logged |
| AD4 | Verify audit timeline export | Export generated; contains custody events |

### 3.5 Audit & Export Validation

| Step | Action | Expected Output |
|---|---|---|
| AU1 | Open audit panel for a record | Timeline includes create/submit/return/approve |
| AU2 | Export audit log | File contains ordered events; timestamps present |

---

## 4. End-to-End Role Checklist

### 4.1 Analyst Checklist

| # | Item | Expected | Status | Evidence |
|---|---|---|---|---|
| A-1 | Create patch draft | Draft saved, `draft` | ☐ | |
| A-2 | Submit patch | Status `awaiting_verifier` | ☐ | |
| A-3 | Create RFI | RFI exists, `open` | ☐ | |
| A-4 | Submit RFI | Status `awaiting_verifier` | ☐ | |
| A-5 | Block self-approval | 403/validation error | ☐ | |

### 4.2 Verifier Checklist

| # | Item | Expected | Status | Evidence |
|---|---|---|---|---|
| V-1 | View analyst submissions | Queue includes analyst items | ☐ | |
| V-2 | Return patch | Status `returned_to_analyst` | ☐ | |
| V-3 | Approve patch | Status `verified` | ☐ | |
| V-4 | Return RFI | Status `returned_to_analyst` | ☐ | |
| V-5 | Approve RFI | Status `verified` | ☐ | |

### 4.3 Admin Checklist

| # | Item | Expected | Status | Evidence |
|---|---|---|---|---|
| AD-1 | View all queue items | Full workspace visibility | ☐ | |
| AD-2 | Promote verified patch | Status `approved`/`promoted` | ☐ | |
| AD-3 | Reject verified patch | Status `rejected` | ☐ | |
| AD-4 | Audit export | File includes custody events | ☐ | |

---

## 5. Edge-Case Matrix

| ID | Scenario | Steps | Expected Result | Status | Notes |
|---|---|---|---|---|---|
| E-1 | Empty dataset | Load workspace with 0 records | UI shows empty-state; no errors | ☐ | |
| E-2 | Unauthorized user | Hit queue endpoint without auth | 401/403 error response | ☐ | |
| E-3 | Non-member | User with no workspace membership | 401/403; no data leakage | ☐ | |
| E-4 | Role-switch mid-session | Analyst → Verifier without refresh | Queue rehydrates; no stale items | ☐ | |
| E-5 | Concurrent updates | Two users update same patch | Stale update returns 409 | ☐ | |
| E-6 | Invalid transition | Attempt disallowed custody change | 409 INVALID_TRANSITION | ☐ | |
| E-7 | Network error on submit | Disconnect during submit | UI shows error; no local optimistic write | ☐ | |

---

## 6. Pass/Fail Script + Signoff Format

### 6.1 Pass/Fail Helper Script

Run the helper to generate a results template:

```bash
./scripts/uat/v256_uat_pass_fail.sh
```

Expected output:
- Prints the path to a new results file in `out/uat/`
- File contains sections mirroring this runbook

### 6.2 Signoff Format

| Role | Name | Date | Decision | Notes |
|---|---|---|---|---|
| Analyst |  |  | ☐ PASS / ☐ FAIL |  |
| Verifier |  |  | ☐ PASS / ☐ FAIL |  |
| Admin |  |  | ☐ PASS / ☐ FAIL |  |
| QA Lead |  |  | ☐ GO / ☐ NO-GO |  |
| Product |  |  | ☐ GO / ☐ NO-GO |  |

---

## 7. Final Go/No-Go Checklist

All must be PASS to ship:

1. All Analyst, Verifier, Admin checklist items are PASS.
2. All edge-case matrix items are PASS.
3. Audit export contains expected custody events.
4. No console errors during core flows.
5. No unauthorized access or data leakage observed.
6. Signoff table completed with GO from QA Lead + Product.

