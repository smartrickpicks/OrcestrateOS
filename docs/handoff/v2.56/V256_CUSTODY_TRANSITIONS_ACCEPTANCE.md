# V2.56 Custody Transitions Acceptance

Date: 2026-02-18  
Branch: `codex/v256-custody-transitions`

## Execution evidence

Test command:

```bash
pytest -q OrcestrateOS/tests/test_custody_transitions.py
```

Result:

- `4 passed in 0.24s`

## Transition matrix pass/fail

| Flow | cURL evidence (endpoint + body) | Expected | Result | Proof |
|---|---|---:|---:|---|
| Patch approve (verifier) | `PATCH /api/v2.5/patches/pat_1` `{"status":"Verifier_Approved","version":2}` | 200 | PASS | `tests/test_custody_transitions.py:455` |
| Patch reject (verifier) | `PATCH /api/v2.5/patches/pat_1` `{"status":"Rejected","version":7}` | 200 | PASS | `tests/test_custody_transitions.py:469` |
| Admin promotion (admin approve) | `PATCH /api/v2.5/patches/pat_1` `{"status":"Admin_Approved","version":3}` | 200 | PASS | `tests/test_custody_transitions.py:459` |
| Admin apply | `PATCH /api/v2.5/patches/pat_1` `{"status":"Applied","version":4}` | 200 | PASS | `tests/test_custody_transitions.py:463` |
| RFI return | `PATCH /api/v2.5/rfis/rfi_1` `{"custody_status":"returned_to_analyst","version":1}` | 200 | PASS | `tests/test_custody_transitions.py:505` |
| RFI resolve | `PATCH /api/v2.5/rfis/rfi_1` `{"custody_status":"resolved","version":3}` | 200 | PASS | `tests/test_custody_transitions.py:513` |
| Correction approve | `PATCH /api/v2.5/corrections/cor_1` `{"status":"approved","version":1}` | 200 | PASS | `tests/test_custody_transitions.py:538` |
| Correction reject | `PATCH /api/v2.5/corrections/cor_1` `{"status":"rejected","version":7}` | 200 | PASS | `tests/test_custody_transitions.py:544` |
| Patch self-approval blocked | `PATCH /api/v2.5/patches/pat_1` `{"status":"Verifier_Approved","version":3}` by author | 403 | PASS | `tests/test_custody_transitions.py:481` |
| RFI role forbidden | `PATCH /api/v2.5/rfis/rfi_1` `{"custody_status":"resolved","version":10}` as analyst | 403 | PASS | `tests/test_custody_transitions.py:519` |
| Correction role forbidden | `PATCH /api/v2.5/corrections/cor_1` `{"status":"approved","version":9}` as analyst | 403 | PASS | `tests/test_custody_transitions.py:550` |
| Patch stale-version | `PATCH /api/v2.5/patches/pat_1` `{"status":"Verifier_Approved","version":1}` | 409 `STALE_VERSION` | PASS | `tests/test_custody_transitions.py:486` |
| RFI stale-version | `PATCH /api/v2.5/rfis/rfi_1` `{"custody_status":"resolved","version":4}` | 409 `STALE_VERSION` | PASS | `tests/test_custody_transitions.py:529` |
| Correction stale-version | `PATCH /api/v2.5/corrections/cor_1` `{"status":"approved","version":3}` | 409 `STALE_VERSION` | PASS | `tests/test_custody_transitions.py:555` |
| Patch invalid transition | `PATCH /api/v2.5/patches/pat_1` `{"status":"Applied","version":5}` from `Submitted` | 409 `INVALID_TRANSITION` | PASS | `tests/test_custody_transitions.py:491` |
| RFI invalid transition | `PATCH /api/v2.5/rfis/rfi_1` `{"custody_status":"open","version":11}` from `awaiting_verifier` | 409 `INVALID_TRANSITION` | PASS | `tests/test_custody_transitions.py:524` |
| Correction invalid transition | `PATCH /api/v2.5/corrections/cor_1` `{"status":"rejected","version":11}` from `approved` | 409 `INVALID_TRANSITION` | PASS | `tests/test_custody_transitions.py:560` |

## UI evidence

- Verifier patch approve/reject calls PATCH writes via `opsDbWriteStatus`: `ui/viewer/index.html:45099`, `ui/viewer/index.html:45133`, `ui/viewer/index.html:39746`.
- Operations queue RFI resolve/return actions call `opsDbWriteRfiStatus`: `ui/viewer/index.html:39592`, `ui/viewer/index.html:39593`, `ui/viewer/index.html:39765`.
- Operations queue correction approve/reject actions call `opsDbWriteCorrectionStatus`: `ui/viewer/index.html:39595`, `ui/viewer/index.html:39596`, `ui/viewer/index.html:39784`.
- Admin lifecycle states (`Verifier_Approved` -> `Admin_Approved` -> `Applied`) are encoded in transition map: `ui/viewer/index.html:14032`, `ui/viewer/index.html:14035`.

## Server contract evidence

- Patch transition matrix and 403/409 guards: `server/routes/patches.py:27`, `server/routes/patches.py:351`, `server/routes/patches.py:372`, `server/routes/patches.py:381`.
- RFI custody transition matrix and 403/409 guards: `server/routes/rfis.py:21`, `server/routes/rfis.py:380`, `server/routes/rfis.py:395`.
- Correction transition guard now returns 409 on invalid transitions: `server/routes/corrections.py:269`, `server/routes/corrections.py:272`.
