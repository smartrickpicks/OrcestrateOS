# V2.56 Field Suggestions UI Fix — Match Matrix Acceptance

## Status: COMPLETE

## Summary
Field Suggestions panel replaced from list-style rendering to a proper table/matrix
with visible column headers, row-level match decisions, deterministic sorting, and
dark-mode-safe tokens. Analyst workflow only — no changes to verifier/admin pages.

## Visual Layout
| Column | Content |
|--------|---------|
| Source Field | Original column header from imported data |
| Suggested Canonical | Best matching glossary term or `—` |
| Match Status | Badge: **Match** (green), **Review** (amber), **No Match** (neutral) |
| Confidence | Percentage + bucket chip (HIGH / MED / LOW) |
| Evidence / Reason | Method chip (Exact, Fuzzy, Keyword, Alias) + category + BODY badge |
| Actions | Accept / Decline buttons for pending; Show for keyword highlighting |

## Match Status Rules
- `match_method == "none"` → always **No Match**
- Confidence ≥ 80% → **Match** (green)
- Confidence ≥ 40% → **Review** (amber)
- Confidence < 40% → **No Match** (neutral)

## Confidence Buckets
- ≥ 80% → HIGH (green)
- ≥ 60% → MED (amber)
- > 0% → LOW (red)
- 0% → none / `—`

## Sorting (Deterministic)
1. Status priority: Review (0) → No Match (1) → Match (2)
2. Confidence descending within same status
3. Source field alphabetical tie-breaker

## Hidden / Low-Signal Section
- Fields with `match_method == "none"` and 0% confidence are collapsed into a
  "Hidden / Low-signal fields (N)" section below the main table
- Expand/collapse toggle with chevron indicator
- Row count always visible

## Dark Mode
- Table headers use `var(--table-head-bg)` / `var(--table-head-text)` tokens
- Status badges use semi-transparent neon palette in dark mode
- Evidence chips use violet-accent dark mode overrides
- Row hover uses `var(--table-row-hover)` token
- Sticky header z-index prevents overlap issues

## Accept / Decline Behavior
- Wired to existing `_syncAccept()` / `_syncReject()` handlers — no changes
- Demo suggestions (id starts with `demo_`) handled locally
- Real suggestions go through `PATCH /api/v2.5/suggestions/{id}` as before

## Key Files
| File | Change |
|------|--------|
| `ui/viewer/index.html` | New `_syncRenderSuggestions`, helper functions, CSS |
| `tests/test_field_suggestions_ui.py` | 40 tests for sorting, status, confidence, evidence |

## Helper Functions (JavaScript)
| Function | Purpose |
|----------|---------|
| `_smGetMatchStatus(sug)` | Returns `match` / `review` / `no-match` |
| `_smGetConfidencePct(sug)` | Returns integer 0-100 |
| `_smGetConfidenceBucket(pct)` | Returns `high` / `med` / `low` / `none` |
| `_smStatusPriority(status)` | Returns 0/1/2 for sort ordering |
| `_smSortSuggestions(list)` | Deterministic multi-key sort |
| `_smGetEvidenceChips(sug)` | Returns array of chip labels |
| `_smToggleHidden()` | Toggle hidden/low-signal section |

## CSS Classes
| Class | Purpose |
|-------|---------|
| `.sync-matrix` | Main table |
| `.sm-status-badge.match/review/no-match` | Status badges |
| `.sm-conf-bucket.high/med/low/none` | Confidence bucket chips |
| `.sm-evidence-chip` | Evidence/reason chips |
| `.sm-hidden-section` | Collapsible low-signal section |

## Test Coverage
- `tests/test_field_suggestions_ui.py` — 40 tests:
  - `TestMatchStatusMapping` (12 tests): boundary conditions, null handling
  - `TestConfidenceBucketMapping` (4 tests): bucket thresholds
  - `TestConfidencePct` (5 tests): direct pct, score conversion, precedence
  - `TestDeterministicSorting` (7 tests): priority ordering, tie-breaking, edge cases
  - `TestStatusPriority` (3 tests): priority values
  - `TestEvidenceChips` (9 tests): method labels, categories, body source

## Validation
- `pytest -q tests/` — 119 passed
- `bash scripts/replit_smoke.sh --allow-diff` — passed
- No regressions in preflight, export, or account resolver flows
