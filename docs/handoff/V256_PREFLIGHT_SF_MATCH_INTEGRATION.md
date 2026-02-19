# V2.56 Preflight Test Lab — Salesforce Match Integration

## Status: COMPLETE

## Summary
Salesforce account match results are now a first-class section in the Preflight Test Lab report, rendered as a matrix-style table immediately after encoding/corruption findings and before remaining preflight sections (metrics, per-page breakdown, etc.).

## Before / After

### Before
```
Preflight Test Lab Report:
  1. Gate badge + doc mode
  2. Why Gate explanation
  3. Reason codes
  4. Corruption samples (encoding)
  5. Key Metrics
  6. Decision Trace
  7. Per-Page Breakdown
  8. Persistence Status
  9. Raw JSON
  10. [async] Field Suggestions section
```

### After
```
Preflight Test Lab Report:
  1. Gate badge + doc mode
  2. Why Gate explanation
  3. Reason codes
  4. Corruption samples (encoding)         ← Encoding findings
  5. ★ Salesforce Account Match (NEW)      ← SF match section
  6. Key Metrics                           ← Remaining preflight
  7. Decision Trace
  8. Per-Page Breakdown
  9. Persistence Status
  10. Raw JSON
  11. [async] Field Suggestions section
```

## Section Ordering Constants
```javascript
PFTL_SECTION_ORDER = {
  encoding: 0,
  salesforce_match: 1,
  missing_required: 2,
  invalid_picklist: 3,
  metrics: 4,
  other: 5
};
```

## Matrix Table Columns (SF Match)
| Column | Content |
|--------|---------|
| Source Text | Extracted header that matched an entity hint |
| Mapped Account | Top candidate account name from CSV index |
| Match Status | Badge: **Match** (green), **Review** (amber), **No Match** (neutral) |
| Confidence | Percentage + bucket chip (HIGH / MED / LOW) |
| Evidence | Match tier chip (Exact, Token Overlap, Edit Distance) + provider + classification |

## Entity Header Detection
Headers are matched against entity hint keywords:
```python
_SF_ENTITY_HINTS = [
    "account name", "account", "client name", "client", "company name",
    "company", "legal name", "legal entity", "entity name", "entity",
    "artist", "artist name", "vendor", "vendor name", "counterparty",
    "customer", "customer name", "payee", "payee name", "licensee",
    "licensor", "party name",
]
```
If no entity headers are found, the first 5 extracted headers are used as fallback.

## Server-Side Payload Shape
The `run_preflight` response now includes `salesforce_match`:
```json
{
  "salesforce_match": [
    {
      "source_field": "Account Name",
      "suggested_label": "Acme Corp",
      "match_method": "exact",
      "match_score": 1.0,
      "confidence_pct": 100,
      "match_status": "match",
      "classification": "matched",
      "candidates": [...],
      "explanation": "Top match: Acme Corp (score=1.0, tier=exact)",
      "provider": "cmg_csv_v1"
    }
  ]
}
```

## Match Status Mapping
- `classification == "matched"` → **match** (green badge)
- `classification == "ambiguous"` → **review** (amber badge)
- `classification == "not_found"` → **no-match** (neutral badge)

## Deterministic Sorting
Results are sorted by:
1. Status priority: review (0) → no-match (1) → match (2)
2. Confidence descending within same status
3. Source field alphabetical tie-breaker

## Reused Components
- `_smGetConfidenceBucket(pct)` — confidence bucket calculation
- `.sync-matrix` — table CSS class with sticky header
- `.sm-status-badge` — match/review/no-match badges
- `.sm-conf-bucket` — HIGH/MED/LOW chips
- `.sm-evidence-chip` — evidence/reason chips
- `_pftlEsc()` — HTML escaping

## Key Files Changed
| File | Change |
|------|--------|
| `server/preflight_engine.py` | Added `_run_salesforce_match()`, `_SF_ENTITY_HINTS`, `salesforce_match` key in `run_preflight` result |
| `ui/viewer/index.html` | Added `_pftlRenderSfMatchSection()`, `PFTL_SECTION_ORDER`, `_pftlSectionPriority()`, inserted call in `_pftlRenderReport` |
| `tests/test_preflight_sf_match.py` | 28 new tests |

## Test Coverage
- `tests/test_preflight_sf_match.py` — 28 tests:
  - `TestSectionOrdering` (8 tests): encoding < sf_match < others, deterministic sort
  - `TestRunSalesforceMatch` (7 tests): payload shape, status values, confidence range, sorting
  - `TestEntityHeaderDetection` (6 tests): entity hints for account/client/artist/vendor/company
  - `TestPreflightResultIncludesSfMatch` (3 tests): key presence, ordering in dict
  - `TestMatrixRowContent` (4 tests): confidence, status, source/target, no-match dash

## Validation
- `pytest -q tests/` — 147 passed
- `bash scripts/replit_smoke.sh --allow-diff` — passed
- No regressions to existing preflight, export, or suggestion flows
- Verifier/admin workflows unchanged (SF match is analyst test lab only)
