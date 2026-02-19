# V2.56 — Salesforce Account Resolver Acceptance

**Branch:** `codex/v256-sf-account-resolver`
**Date:** 2026-02-19

---

## Scope

Deterministic account matching for analyst preflight using CMG_Account.csv (14,385 rows).
Analyst triage only — no verifier/admin workflow changes.

## Changed Files

| File | Change |
|------|--------|
| `server/data/CMG_Account.csv` | Added: 14,385-row account reference data |
| `server/resolvers/account_index.py` | New: CSV loader, NFKC normalization, multi-field index |
| `server/resolvers/salesforce.py` | Upgraded: stub → CSV-backed resolver with exact/fuzzy matching |
| `server/routes/preflight.py` | Added: `/resolve-account`, `/resolve-accounts-batch`, `/resolver-status` endpoints |
| `ui/viewer/index.html` | Added: `ACCOUNT_MATCH_*` reason labels, `_p1dRunAccountResolver()`, batch resolution UI hook |
| `tests/test_account_resolver.py` | New: 16 deterministic tests |
| `tests/test_suggestion_engine.py` | Updated: Salesforce resolver tests adapted from stub to CSV-backed |
| `tests/test_drive_export_conventions.py` | Fixed: incomplete auth mock (pre-existing test isolation bug) |
| `tests/test_drive_batch_ingest.py` | Fixed: incomplete auth mock (pre-existing test isolation bug) |

## Implementation

### 1. CSV Loader + Normalized Index (`server/resolvers/account_index.py`)
- Loads `CMG_Account.csv` at first access (lazy singleton)
- Indexes 4 name fields: Account Name, Artist Name, Company Name, Legal Name
- Normalization: NFKC → lowercase → strip punctuation → collapse whitespace
- Builds exact-match map and per-record token sets

### 2. Resolver (`server/resolvers/salesforce.py`)
- 3-tier matching: Exact → Token Overlap (Jaccard) → Edit Distance (Levenshtein)
- Thresholds: exact=1.0, token=0.65, edit_distance=0.75, ambiguous_gap=0.10
- Classifications: `matched` | `ambiguous` | `not_found`
- Stable sort: score DESC, account_id ASC
- Max 5 candidates returned
- Provider: `cmg_csv_v1`
- Offline-only, no network calls

### 3. API Endpoints (`server/routes/preflight.py`)
- `POST /api/preflight/resolve-account` — single account resolution
- `POST /api/preflight/resolve-accounts-batch` — batch (up to 200 names)
- `GET /api/preflight/resolver-status` — index health check

### 4. UI Integration (`ui/viewer/index.html`)
- `_REASON_LABELS`: `ACCOUNT_MATCH_RESOLVED`, `ACCOUNT_MATCH_AMBIGUOUS`, `ACCOUNT_MATCH_NOT_FOUND`
- `_p1dRunAccountResolver()`: called after triage render, batch-resolves extracted account names
- `_p1dBuildAccountFinding()`: builds finding objects for ambiguous/not_found results
- Results cached in `_acctResolverCache` to avoid redundant calls

## Non-Regression

- Existing `MISSING_REQUIRED` / `PICKLIST_INVALID` / `OCR_MOJIBAKE` paths unchanged
- Verifier queue, admin promotion, custody logic untouched
- All 79 tests pass (16 new + 63 existing)

## Acceptance Checklist

| # | Criterion | Status |
|---|-----------|--------|
| 1 | CMG_Account.csv loads (14,385 accounts) | PASS |
| 2 | Normalization is NFKC-safe and deterministic | PASS |
| 3 | Exact match: "Louis The Child" → matched, score=1.0 | PASS |
| 4 | Exact match case-insensitive: "louis the child" = "LOUIS THE CHILD" | PASS |
| 5 | Cross-field match: legal name "Brandon Green" → Maejor | PASS |
| 6 | Not found: "Completely Nonexistent Artist" → not_found | PASS |
| 7 | Fuzzy match: "Luis The Child" → scored >0.7 | PASS |
| 8 | Stable ordering: same input → same candidate order every run | PASS |
| 9 | Candidates capped at 5 | PASS |
| 10 | Empty query → not_found, no crash | PASS |
| 11 | Contract fields present in candidate dicts | PASS |
| 12 | Existing preflight tests still pass | PASS |
| 13 | `pytest -q` all 79 tests pass | PASS |
| 14 | Smoke test passes | PENDING |

## Known Gaps

- Pre-existing test isolation issue in `test_drive_export_conventions.py` and `test_drive_batch_ingest.py` (incomplete auth mock) — fixed as part of this branch.
- Address field matching not implemented (CSV has no address columns). Resolver accepts `address` parameter but does not use it.
- No Salesforce live API integration — resolver is CSV-only (`cmg_csv_v1`).

## Validation Commands

```bash
pytest tests/ -q                           # 79 passed
bash scripts/replit_smoke.sh --allow-diff  # OK
```
