# V2.56.x — Preflight Resolution Story: P0 Implementation Handoff

**Date:** 2026-02-19
**Status:** COMPLETE — P0 Backend Contract + Ranking
**Scope:** P0-1 through P0-7 from V256_PREFLIGHT_RESOLUTION_STORY_CLARITY.md

---

## What Changed

### P0-1: `build_resolution_story()` — `server/preflight_engine.py`

New function that assembles a resolution story from `_run_salesforce_match()` output.

**CMG-side gating (locked rule):**
- `_CMG_KNOWN_ALIASES`: hardcoded set of known CMG entity names (Ostereo Limited, Ostereo Publishing Limited, + Asterio variants)
- `_CMG_ACCOUNT_TYPES`: account types indicating CMG entities (currently: "division")
- `_is_cmg_side(candidate_name, sf_candidates)`: checks alias set OR account type from CSV record
- Legal entity selection: filters to CMG candidates, sorts by (match_status priority, -confidence), picks top
- If no CMG candidate qualifies: `legal_entity_account = null`, `requires_manual_confirmation = true`

**Counterparty selection:**
- All non-CMG candidates with `composite >= REVIEW_THRESHOLD (0.40)` promoted to `counterparties[]`
- Multi-counterparty supported — no single-winner constraint

**Reasoning and actions:**
- Generates per-entity reasoning steps citing source type and role assignment
- Generates analyst actions (confirm/no-action) based on match status
- Adds suppression reasoning for service-penalty candidates
- Adds address evidence reasoning when detected

### P0-2: `_guess_agreement_type()` — `server/preflight_engine.py`

Keyword-based heuristic scanning title zone (first 10 lines, weight 3.0) and body (weight 1.0).
Returns one of: `distribution`, `license`, `recording`, `publishing`, `management`, `service`, `amendment`, `unknown`.

### P0-3: `recital_parties` stub

Always `[]` in V1. Field present in payload for forward compatibility.

### P0-4: `resolution_story` in `run_preflight()`

- `build_resolution_story(sf_match, full_text)` called after `_run_salesforce_match()`
- New `resolution_story` key added to return dict
- `salesforce_match` key preserved unchanged
- Empty-pages case (`run_preflight([])`) does NOT include `resolution_story` (no data to resolve)

### P0-5: Per-candidate fields on `salesforce_match[]` rows

- `label_value_hit` (bool): `true` when `source_type == "strict_label_value"`
- `recital_party_hit` (bool): always `false` in V1 (stub for P1 recital parsing)

---

## Files Changed

| File | Change Type |
|---|---|
| `server/preflight_engine.py` | Added: `_CMG_KNOWN_ALIASES`, `_CMG_ACCOUNT_TYPES`, `_is_cmg_side()`, `_AGREEMENT_TYPE_KEYWORDS`, `_guess_agreement_type()`, `build_resolution_story()`, `_source_type_label()`. Modified: `_run_salesforce_match()` (added `label_value_hit`, `recital_party_hit`), `run_preflight()` (added `resolution_story` to return). |
| `tests/test_preflight_sf_match.py` | Added 38 new tests in 6 new classes: `TestPerCandidateExplainabilityFields`, `TestCmgSideGating`, `TestAgreementTypeGuess`, `TestBuildResolutionStory`, `TestResolutionStoryInPreflight`. |
| `docs/handoff/V256_PREFLIGHT_RESOLUTION_STORY_P0_IMPL.md` | This file. |

---

## Test Results

```
pytest tests/ -x --tb=short -q
292 passed in 74.07s
```

- Previous: 254 tests (135 SF-specific)
- Now: 292 tests (173 SF-specific, +38 new)
- Zero failures, zero regressions

```
bash scripts/replit_smoke.sh --allow-diff
OK: configuration valid
OK: preview wrote out/sf_packet.preview.json (mode: baseline)
OK: preview output matches expected (normalized).
```

Smoke test passes with zero diff.

---

## Locked Rules Enforced

1. **CMG-side gating**: `legal_entity_account` is always CMG-side. If no CMG candidate passes, `legal_entity_account = null` + `requires_manual_confirmation = true`.
2. **Role selection independent of table sort**: `build_resolution_story()` applies its own sort (by match_status then confidence) — does not read table render order.
3. **No route changes**: No endpoints added or modified.
4. **No existing field removal**: `salesforce_match` payload shape preserved with two additive fields.
5. **No verifier/admin flow changes**: Resolution story is informational only.

---

## What's NOT in P0

- P1: Frontend rendering (Sections A–D, badges, collapse behavior)
- P2: Recital party parsing, confirmation buttons, export integration
- CMG alias management UI (aliases are hardcoded for now)
- `business_unit` and `parent_account` population (stubbed as `null`)

---

## Next Steps (P1)

1. Render `resolution_story` in preflight modal UI (Sections A–D)
2. Wire badge system (Legal Entity, Counterparty, Multi-Counterparty, Manual Confirmation)
3. Collapse Full Match Table by default when story is available
4. Wire into `prep_export_v0` JSON export
