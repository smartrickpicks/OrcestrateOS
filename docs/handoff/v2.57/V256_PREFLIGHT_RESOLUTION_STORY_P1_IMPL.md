# V2.56.x — Preflight Resolution Story: P1 Implementation Handoff

**Date:** 2026-02-19
**Status:** COMPLETE — P1 Frontend Narrative + Explainability
**Scope:** P1 tasks 1–6 from the V256_PREFLIGHT_RESOLUTION_STORY_CLARITY.md spec

---

## What Changed

### Section A: Who We Think This Is

Renders structured entity cards from `resolution_story`:

- **Legal entity card**: Green left border, entity name, "Legal Entity" badge (green), match status badge, confidence percentage. Empty-state shows italic "no CMG-side entity identified" when `legal_entity_account` is null.
- **Counterparty cards**: Purple left border, entity name, "Counterparty" badge (purple), match status badge, confidence percentage. When `counterparties.length > 1`, each row also shows a "Multi-Counterparty" badge (violet).
- **Business Unit / Parent Account rows**: Shown below entity cards, displays value or "none detected" placeholder.
- **Manual Confirmation Required badge**: Orange badge shown when `requires_manual_confirmation === true`.

### Section B: Why We Think That

Renders `reasoning_steps[]` as a numbered list with styled step numbers and prose text. Each step cites the evidence source (label:value extraction, CSV phrase scan, etc.) and the role assignment.

### Section C: What This Agreement Appears To Be

Shows `agreement_type_guess` capitalized (e.g., "Distribution Agreement"). Displays source note "(inferred from title + body keywords)". Shows "Unknown Agreement Type" when type is `unknown`.

### Section D: What Needs Analyst Action

Renders `analyst_actions[]` with contextual icons:
- Green checkmark for "no action required" items
- Orange warning for "confirm" / "review" items
- Red X for "manual" lookup items

### Full Match Table Collapse

When `resolution_story` exists in the preflight response:
- The existing Salesforce match table is wrapped in a collapsible container, **collapsed by default**
- A "Show Full Match Table" / "Hide Full Match Table" toggle button appears above
- The toggle arrow rotates and label text updates on click
- When `resolution_story` is absent, the table renders exactly as before (no toggle, always visible)
- All existing table features preserved: rows, chips, hidden bucket, Debug toggle

### Badge System

| Badge | CSS Class | When Shown |
|---|---|---|
| Legal Entity | `rs-badge-legal` (green) | Always on legal entity card |
| Counterparty | `rs-badge-counter` (purple) | On each counterparty card |
| Multi-Counterparty | `rs-badge-multi` (violet) | On counterparty cards when > 1 counterparty |
| Manual Confirmation Required | `rs-badge-manual` (orange) | When `requires_manual_confirmation === true` |

### Dark Mode

All Resolution Story elements use CSS custom properties (`var(--bg-2)`, `var(--border-1)`, `var(--text-1)`, etc.) with explicit `html[data-theme="dark"]` overrides for:
- Section backgrounds and borders
- Entity card backgrounds and accent borders
- Badge colors (green, purple, violet, orange variants)
- Reasoning step numbers and text
- Toggle button styling

### Empty / Error States

- No resolution_story key → no story section rendered, table shows as before
- Empty salesforce_match → no story or table section rendered
- Null legal_entity_account → empty-state card with italic placeholder
- Empty counterparties → only legal entity card shown (no counterparty section)
- No reasoning_steps → Section B omitted
- No analyst_actions → Section D omitted

---

## Before / After

### Before (P0)

```
Gate Badge + Encoding Findings
Corruption Samples
Salesforce Account Match Table (always visible, flat rows)
Key Metrics
Decision Trace
Per-Page Breakdown
Persistence Status
Raw JSON
```

### After (P1)

```
Gate Badge + Encoding Findings
Corruption Samples
+----------------------------------------------------------+
| A. WHO WE THINK THIS IS                                   |
|   [Legal Entity badge] Ostereo Limited (91%) Match        |
|   [Counterparty badge] 1888 Records (87%) Match           |
|   Business Unit: — none detected —                        |
|   Parent Account: — none detected —                       |
+----------------------------------------------------------+
| B. WHY WE THINK THAT                                      |
|   1. "Ostereo Limited" identified as CMG-side entity...   |
|   2. "1888 Records" extracted via strict label:value...   |
+----------------------------------------------------------+
| C. WHAT THIS AGREEMENT APPEARS TO BE                      |
|   Distribution Agreement                                  |
|   (inferred from title + body keywords)                   |
+----------------------------------------------------------+
| D. WHAT NEEDS ANALYST ACTION                              |
|   ✓ Legal entity "Ostereo Limited" — no action required  |
|   ✓ Counterparty "1888 Records" — no action required     |
+----------------------------------------------------------+
[▸ Show Full Match Table]  ← collapsed by default
  (existing table with all rows, chips, debug, hidden bucket)
Key Metrics
Decision Trace
Per-Page Breakdown
Persistence Status
Raw JSON
```

---

## Files Changed

| File | Change Type |
|---|---|
| `ui/viewer/index.html` | Added: CSS styles for `.rs-*` classes (light + dark mode). Added: `_pftlRenderResolutionStory()`, `_pftlRenderStoryWho()`, `_pftlRenderStoryWhy()`, `_pftlRenderStoryWhat()`, `_pftlRenderStoryAction()`, `pftlToggleSfTable()`. Modified: `_pftlRenderSfMatchSection()` (added collapse wrapper when story exists). Modified: preflight modal builder (inserted `_pftlRenderResolutionStory(r)` call before SF match table). |
| `docs/handoff/v2.57/V256_PREFLIGHT_RESOLUTION_STORY_P1_IMPL.md` | This file. |

---

## Validation Results

```
PYTHONPATH=. pytest -q tests/test_preflight_sf_match.py
173 passed in 77.89s
```

```
bash scripts/replit_smoke.sh --allow-diff
OK: configuration valid
Wrote preview to out/sf_packet.preview.json
OK: preview wrote out/sf_packet.preview.json (mode: baseline)
OK: preview output matches expected (normalized).
```

Zero failures, zero regressions.

---

## Constraints Honored

1. **No route changes**: No endpoints added or modified.
2. **No backend API contract changes**: `resolution_story` and `salesforce_match` payloads unchanged from P0.
3. **No verifier/admin workflow changes**: Resolution story is informational-only.
4. **No existing table column/chip/debug removal**: All existing SF match table features preserved.
5. **Backward compatible**: When `resolution_story` is absent, UI renders identically to pre-P1.

---

## Known Limitations

1. `business_unit` and `parent_account` are always `null` (backend stubs). UI shows "none detected" placeholder.
2. `recital_parties` stub is empty — no recital section rendered yet (P2).
3. No confirmation buttons — story is informational only in V1 (P2).
4. No export integration — `resolution_story` is not yet wired into `prep_export_v0` (P2).
5. No frontend-specific test harness exists — validation is via backend tests and visual inspection.

---

## Next Steps (P2)

1. Recital party parsing and rendering
2. Confirmation buttons on analyst actions
3. Wire `resolution_story` into `prep_export_v0` JSON export
4. CMG alias management UI
