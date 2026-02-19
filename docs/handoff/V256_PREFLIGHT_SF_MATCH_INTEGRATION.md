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
| Source Text | Extracted account **value** (e.g., "1888 Records"), not the label |
| Mapped Account | Top candidate account name from CSV index |
| Match Status | Badge: **Match** (green), **Review** (amber), **No Match** (neutral) |
| Confidence | Percentage + bucket chip (HIGH / MED / LOW) |
| Evidence | Match tier chip (Exact, Token Overlap, Edit Distance) + provider + classification |

## Candidate Extraction (Value Over Label)
The engine extracts actual account values from body text using `extract_account_candidates(full_text, extracted_headers)`:

**Priority order:**
1. **Label:value patterns** — Regex matches like "Account Name: 1888 Records" → extracts "1888 Records"
2. **Non-label headers** — Headers that aren't pure entity labels (filtered by `_SF_STOP_LABELS`)
3. **Fallback** — First 5 headers if nothing else found

**Stop-label filtering** (`_SF_STOP_LABELS`):
Pure labels like "Account Name", "Account Name:", "payments/accounting", "N/A", "TBD" are excluded.

**Label:value regex** (`_LABEL_VALUE_RE`):
Matches entity hint keywords followed by `:`, `;`, `-`, `–`, or `—` separator, capturing the value portion.

**Normalization:**
- Trim whitespace, collapse repeated spaces
- Strip trailing punctuation (`:`, `;`, `,`)
- Case-insensitive deduplication

**JS mirror:** `_pftlExtractAccountCandidates(extractedText, extractedHeaders)` replicates the same logic client-side.

## Entity Header Hints
Used for label:value pattern matching:
```python
_SF_ENTITY_HINTS = [
    "account name", "account", "client name", "client", "company name",
    "company", "legal name", "legal entity", "entity name", "entity",
    "artist", "artist name", "vendor", "vendor name", "counterparty",
    "customer", "customer name", "payee", "payee name", "licensee",
    "licensor", "party name",
]
```

## Server-Side Payload Shape
The `run_preflight` response now includes `salesforce_match`:
```json
{
  "salesforce_match": [
    {
      "source_field": "1888 Records",
      "suggested_label": "1888 Records",
      "match_method": "exact",
      "match_score": 1.0,
      "confidence_pct": 100,
      "match_status": "match",
      "classification": "matched",
      "candidates": [...],
      "explanation": "Top match: 1888 Records (score=1.0, tier=exact)",
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
| `server/preflight_engine.py` | Added `extract_account_candidates()`, `_SF_STOP_LABELS`, `_LABEL_VALUE_RE`, `_normalize_candidate()`, updated `_run_salesforce_match()` to accept `full_text` and use candidate extraction |
| `ui/viewer/index.html` | Added `_pftlExtractAccountCandidates()`, `_PFTL_STOP_LABELS`, `_PFTL_LABEL_VALUE_RE`, `_pftlRenderSfMatchSection()`, `PFTL_SECTION_ORDER`, `_pftlSectionPriority()` |
| `tests/test_preflight_sf_match.py` | 45 tests (expanded from 28) |

## Test Coverage
- `tests/test_preflight_sf_match.py` — 45 tests:
  - `TestSectionOrdering` (8 tests): encoding < sf_match < others, deterministic sort
  - `TestExtractAccountCandidates` (13 tests): value-over-label extraction, normalization, dedup, stop-labels, fallback
  - `TestRunSalesforceMatch` (8 tests): payload shape, status values, confidence range, sorting, source_field shows value
  - `TestEntityHeaderDetection` (6 tests): entity hints for account/client/artist/vendor/company
  - `TestPreflightResultIncludesSfMatch` (3 tests): key presence, ordering in dict
  - `TestMatrixRowContent` (4 tests): confidence, status, source/target, no-match dash
  - `TestAcceptanceCriteria` (3 tests): 1888 Records extraction, label exclusion, unknown value no-match

## Validation
- `pytest -q tests/` — 164 passed
- `bash scripts/replit_smoke.sh --allow-diff` — passed
- No regressions to existing preflight, export, or suggestion flows
- Verifier/admin workflows unchanged (SF match is analyst test lab only)
