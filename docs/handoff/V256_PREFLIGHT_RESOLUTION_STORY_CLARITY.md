# V2.56.x — Preflight Resolution Story: Clarity Document

**Date:** 2026-02-19
**Status:** DRAFT — Clarity & Design Only (No Code Changes)
**Author:** Agent
**Scope:** Analyst-facing preflight narrative flow: WHO → WHY → WHAT → ACTION

---

## 1. Audit Snapshot (Current Pain Points)

### 1.1 Noisy Salesforce Account Match Output

The current preflight Salesforce match pipeline (`_run_salesforce_match`) produces a flat table of candidate rows. While v2.57 calibration (hard denylist, source-type tracking, composite scoring) significantly improved ranking, the output remains a raw ranked table with no narrative framing.

**Observed problems before v2.57 calibration:**

| Pain Point | Example | Root Cause |
|---|---|---|
| Legal boilerplate tokens ranked as candidates | "Distribution", "Trademark", "DELAY", "Image", "Mean" appearing above real accounts | No hard denylist; header-fallback extraction treated any capitalized token as a candidate |
| True counterparties buried | "1888 Records" ranked below noise tokens from same document | No source-type priority; header_fallback noise scored equally with csv_phrase_hit and strict_label_value |
| Address evidence applied globally | A street address on page 1 boosted a candidate mentioned on page 8 | Address scoring used full-page presence instead of candidate-local proximity windows |
| Service penalty over-applied | "Atlantic Records" penalized because "Spotify" appeared in a DSP list 3 paragraphs away | No source-aware caps; no proximity windowing on service context |
| Single-token generic noise | "Record", "Company", "Account" treated as real candidates | No generic-token detection or status cap |

**V2.57 calibration addressed most ranking issues but these UX gaps remain:**

1. **Table-only output, no narrative reasoning.** Analysts see rows of data with chips and percentages. There is no prose explanation of "who is this contract between and why do we think so." Analysts must mentally reconstruct the entity resolution story from chip codes.

2. **No multi-counterparty framing.** A distribution agreement between "1888 Records" and "Universal Music Group" with "Spotify" as a DSP shows all three in the same flat table. There is no structural distinction between the legal entity, the counterparty, and a platform mentioned in a service clause.

3. **No agreement-type inference.** The preflight knows the document mentions "Distribution Agreement" in recitals but does not surface this as a structured field. Analysts must read the raw text.

4. **No manual-confirmation gating.** Low-confidence matches (review status) flow through identically to high-confidence matches. There is no mechanism for an analyst to confirm or reject a proposed resolution before it enters downstream workflows.

5. **No recital-party parsing.** The recital block (WHEREAS clauses, "between X and Y" patterns) is the highest-signal source for entity identification, but the current extraction pipeline does not specifically parse it. Recital parties would be Priority 1 in a proper resolution hierarchy.

6. **Debug toggle is developer-facing.** The v2.57 Debug button shows `source_type` and `scoring_breakdown` but uses raw JSON-style formatting. This is useful for calibration but not for analyst consumption.

### 1.2 Summary

The v2.57 scoring engine produces correct rankings in most cases (254 tests passing, 135 SF-specific). The gap is *presentation and narrative*: the engine knows the answer but communicates it as a data table rather than a decision story.

---

## 2. Canonical Terms Contract

These terms are locked for all resolution-story features. All backend payloads, UI labels, and documentation must use these exact terms.

| Term | Definition | Usage |
|---|---|---|
| `legal_entity_account` | The primary Salesforce account that owns or originates the contract. Typically the "first party" or the entity on whose behalf the agreement is executed. | Exactly one per resolution. May be `null` if unresolvable. |
| `counterparty_account` | A Salesforce account representing the other party (or parties) to the agreement. | Zero or more per resolution. Supports multi-counterparty contracts. |
| `business_unit` | An organizational subdivision of the legal entity (e.g., "Atlantic Records" as a division of "Warner Music Group"). | Optional. Populated only when the document or CSV data indicates a parent-child relationship. |
| `parent_account` | The top-level Salesforce account in a corporate hierarchy. | Optional. Derived from CSV `parent_account_name` field or Salesforce hierarchy data if available. |
| `recital_parties` | Named entities extracted from the recital/preamble block of the contract (WHEREAS clauses, "by and between" patterns). | Array of `{name, role_hint}` where `role_hint` is "first_party", "second_party", or "unknown". Not yet matched to Salesforce — raw extraction only. |
| `agreement_type_guess` | A best-effort classification of the contract type based on title, recital text, and body keywords. | One of: `distribution`, `license`, `recording`, `publishing`, `management`, `service`, `amendment`, `unknown`. Always a guess — never authoritative. |
| `reasoning_steps` | An ordered list of prose sentences explaining the resolution logic. | Array of strings. Each step corresponds to one evidence signal or decision. |
| `analyst_actions` | Specific next steps the analyst should take. | Array of strings. May include "Confirm legal entity", "Review counterparty match", "Manual lookup required", etc. |
| `requires_manual_confirmation` | Boolean flag indicating the resolution has insufficient confidence for automatic acceptance. | `true` when: no candidate reaches `match` status, or multiple candidates are in `review` status with close scores, or recital parsing disagrees with scored candidates. |

---

## 3. Unified Story IA (Before / After)

### 3.1 Before (Current State)

```
┌─────────────────────────────────────────────────────────┐
│  Preflight Modal                                        │
│  ┌───────────────────────────────────────────────────┐  │
│  │  Gate Badge (GREEN/YELLOW/RED)                    │  │
│  │  Encoding Findings (mojibake, replacement chars)  │  │
│  │  Page Classification Table                        │  │
│  ├───────────────────────────────────────────────────┤  │
│  │  Salesforce Account Match Table                   │  │
│  │  ┌─────────┬──────────┬────────┬──────┬────────┐ │  │
│  │  │ Source   │ Mapped   │ Status │ Conf │ Chips  │ │  │
│  │  │ Text    │ Account  │        │  %   │        │ │  │
│  │  ├─────────┼──────────┼────────┼──────┼────────┤ │  │
│  │  │ row 1   │ ...      │ ...    │ ...  │ ...    │ │  │
│  │  │ row 2   │ ...      │ ...    │ ...  │ ...    │ │  │
│  │  │ ...     │ ...      │ ...    │ ...  │ ...    │ │  │
│  │  └─────────┴──────────┴────────┴──────┴────────┘ │  │
│  │  [Debug toggle] → raw scoring_breakdown           │  │
│  └───────────────────────────────────────────────────┘  │
│  [Export] [Close]                                        │
└─────────────────────────────────────────────────────────┘
```

**Problems with Before:**
- No narrative structure — analyst must interpret raw table
- No role assignment (legal entity vs. counterparty vs. platform)
- No agreement type surfacing
- No manual confirmation workflow
- Debug toggle is developer-facing, not analyst-facing

### 3.2 After (Target State)

```
┌─────────────────────────────────────────────────────────────┐
│  Preflight Modal                                            │
│  ┌───────────────────────────────────────────────────────┐  │
│  │  Gate Badge + Encoding Findings (unchanged)           │  │
│  │  Page Classification Table (unchanged)                │  │
│  ├───────────────────────────────────────────────────────┤  │
│  │                                                       │  │
│  │  ┌─── A. WHO WE THINK THIS IS ────────────────────┐  │  │
│  │  │  Legal Entity:  [Badge] 1888 Records (87%)      │  │  │
│  │  │  Counterparty:  [Badge] Universal Music (72%)   │  │  │
│  │  │  Business Unit: — none detected —               │  │  │
│  │  │  Parent Account: — none detected —              │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  ┌─── B. WHY WE THINK THAT ───────────────────────┐  │  │
│  │  │  1. "1888 Records" found via label:value        │  │  │
│  │  │     (Account Name: 1888 Records) — high trust   │  │  │
│  │  │  2. Address "123 Music Row, Nashville TN 37203" │  │  │
│  │  │     verified within 60 chars of mention         │  │  │
│  │  │  3. "Universal Music" found via CSV phrase      │  │  │
│  │  │     match in recital block                      │  │  │
│  │  │  4. "Spotify" suppressed — DSP service mention  │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  ┌─── C. WHAT THIS AGREEMENT APPEARS TO BE ───────┐  │  │
│  │  │  Type: Distribution Agreement                   │  │  │
│  │  │  (inferred from title + recital keywords)       │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  ┌─── D. WHAT NEEDS ANALYST ACTION ───────────────┐  │  │
│  │  │  ⚠ Confirm counterparty "Universal Music" —    │  │  │
│  │  │    confidence below match threshold (72%)       │  │  │
│  │  │  ✓ Legal entity "1888 Records" — high conf.    │  │  │
│  │  └────────────────────────────────────────────────┘  │  │
│  │                                                       │  │
│  │  [▸ Show Full Match Table] ← collapsed by default    │  │
│  │  ┌───────────────────────────────────────────────┐   │  │
│  │  │  (existing table with all rows, chips, debug) │   │  │
│  │  └───────────────────────────────────────────────┘   │  │
│  │                                                       │  │
│  └───────────────────────────────────────────────────────┘  │
│  [Export] [Close]                                            │
└─────────────────────────────────────────────────────────────┘
```

**Render order (locked):**
- **A. Who We Think This Is** — structured entity cards with role badges
- **B. Why We Think That** — ordered reasoning steps in plain prose
- **C. What This Agreement Appears To Be** — agreement type with source
- **D. What Needs Analyst Action** — actionable items with severity indicators
- **Full Match Table** — collapsed by default, available for deep inspection

---

## 4. Data Contract (Backend Response)

### 4.1 Top-Level: `resolution_story` Object (PROPOSED ADDITION)

The existing `run_preflight()` response in `server/preflight_engine.py` currently returns `salesforce_match` as a flat array. The resolution story extends this by adding a **new** `resolution_story` sibling key. The `salesforce_match` array is **preserved unchanged** for backward compatibility. All fields below are **proposed additions** — none exist in the current codebase.

```jsonc
{
  // ... existing preflight fields unchanged ...
  "salesforce_match": [ /* existing array — unchanged */ ],

  "resolution_story": {
    "legal_entity_account": {
      "id": "sf_001ABC",           // Salesforce Account ID or null
      "name": "1888 Records",     // Display name
      "confidence": 0.87,         // Composite score (0.0–1.0)
      "match_status": "match",    // match | review | no-match
      "source_type": "strict_label_value"
    },
    "counterparties": [
      {
        "id": "sf_002DEF",
        "name": "Universal Music Group",
        "confidence": 0.72,
        "match_status": "review",
        "source_type": "csv_phrase_hit"
      }
    ],
    "business_unit": null,          // string or null
    "parent_account": null,         // string or null
    "agreement_type_guess": "distribution",
    "reasoning_steps": [
      "\"1888 Records\" extracted via strict label:value (Account Name: 1888 Records) — high-trust source.",
      "Address \"123 Music Row, Nashville TN 37203\" verified within 150-char proximity window — full address match (0.30).",
      "\"Universal Music Group\" found via CSV phrase scan in document body — medium-trust source.",
      "\"Spotify\" suppressed — recognized as DSP platform with service-context penalty (0.35).",
      "\"Distribution\" suppressed — hard denylist term (legal boilerplate)."
    ],
    "analyst_actions": [
      "Confirm counterparty \"Universal Music Group\" — confidence (72%) below automatic match threshold.",
      "Legal entity \"1888 Records\" passed automatic match — no action required."
    ],
    "requires_manual_confirmation": true,
    "recital_parties": [
      {"name": "1888 Records LLC", "role_hint": "first_party"},
      {"name": "Universal Music Distribution", "role_hint": "second_party"}
    ]
  }
}
```

### 4.2 Per-Candidate Explainability Fields

Each entry in the existing `salesforce_match[]` array already contains `evidence_chips`, `scoring_breakdown`, `source_type`, and `visible`. The following fields are **already present** in the current payload (no additions needed):

| Field | Type | Current Status |
|---|---|---|
| `evidence_chips` | `string[]` | ✅ Present — `name_exact`, `name_fuzzy`, `address_partial`, `address_verified`, `account_context`, `service_context_penalty`, `city_match`, `zip_match` |
| `scoring_breakdown` | `object` | ✅ Present — `{name_evidence, address_evidence, account_context_evidence, service_context_penalty}` |
| `source_type` | `string` | ✅ Present — `strict_label_value`, `csv_phrase_hit`, `header_fallback` |
| `visible` | `boolean` | ✅ Present — `composite >= 0.25` |
| `match_status` | `string` | ✅ Present — `match`, `review`, `no-match` |

**New fields to add per candidate (PROPOSED — do not exist in current codebase):**

| Field | Type | Description |
|---|---|---|
| `recital_party_hit` | `boolean` | Whether this candidate was also found in recital-party extraction |
| `label_value_hit` | `boolean` | Whether this candidate was extracted via strict label:value regex |
| `account_context_hit` | `boolean` | Whether account-context cues were found near this candidate |
| `score_breakdown` | `object` | Extended breakdown: `{name, address, recital, context, penalties, total}` |

### 4.3 Endpoint Strategy

**No new endpoints.** The `resolution_story` object is added to the existing preflight response from `run_preflight()`. The assembly logic lives in a new function `build_resolution_story(salesforce_match, full_text, recital_parties)` called after `_run_salesforce_match()` returns.

---

## 5. Match Priority Rules (Deterministic)

### 5.1 Extraction Priority

| Priority | Source | Description | Trust Level |
|---|---|---|---|
| **P1** | Recital party block parse | Parse "by and between X and Y", WHEREAS clauses. NEW — not yet implemented. | Highest |
| **P2** | Strict label:value pairs | `_STRICT_LABEL_VALUE_RE` anchored to line start. Accepted labels: Account Name, Company Name, Artist Name, Legal Name (+ Salesforce variants). | High |
| **P3** | CSV phrase scan | `_csv_phrase_scan()` matches known account names from `CMG_Account.csv` in body text with word-boundary enforcement. | Medium |
| **P4** | Header fallback | Non-label extracted headers, filtered by stop-labels, generic noise, and prose rejection. | Low |

### 5.2 Scoring Pipeline

Each extracted candidate is scored by `score_candidate()` in `context_scorer.py`:

```
composite = name_evidence (≤ 0.55)
           + address_evidence (≤ 0.30)
           + account_context (≤ 0.20)
           - service_penalty (≤ 0.35)
```

### 5.3 Multi-Counterparty Support

The system does **not** force a single winner. All candidates with `composite >= DISPLAY_THRESHOLD (0.25)` are retained and displayed. The resolution story selects:

- **legal_entity_account**: The highest-scoring candidate with `match` status and `source_type` of `strict_label_value` or `csv_phrase_hit`. If no `match`-status candidate exists, the highest `review`-status candidate with `source_type != header_fallback`.
- **counterparties[]**: All remaining candidates with `composite >= REVIEW_THRESHOLD (0.40)` that are not the selected legal entity and not suppressed by service penalty.

### 5.4 Confidence Threshold Behavior

| Composite Score | Status | Behavior |
|---|---|---|
| `>= 0.65` (with safe name) | `match` | Automatic acceptance. No analyst action required unless `requires_manual_confirmation` is forced by other signals. |
| `>= 0.40` | `review` | Analyst must confirm. Included in `analyst_actions` list. |
| `< 0.40` but `>= 0.25` | `no-match` (visible) | Displayed in full table but not promoted to resolution story entities. |
| `< 0.25` | Hidden | Not displayed in main table. Available in hidden/debug section. |

### 5.5 Service/Platform Exclusion Policy

- Known DSP names (`_DSP_NAMES`: Spotify, Apple Music, Amazon Music, TikTok, YouTube, etc.) receive automatic `service_penalty_max (0.35)`.
- Non-DSP candidates near service-context phrases receive proportional penalty.
- Source-aware caps prevent over-penalization of legitimate entities:
  - `strict_label_value` source: penalty capped at 0.08
  - `csv_phrase_hit` source: penalty capped at 0.15 (unless known DSP)
  - `header_fallback` source: no cap
- Generic/common tokens (`_HARD_DENYLIST`) are suppressed entirely unless extracted via `strict_label_value`.

### 5.6 Sorting Order (Locked)

```python
results.sort(key=lambda r: (
    _SOURCE_TYPE_PRIORITY[r["source_type"]],     # strict=0, csv=1, header=2
    0 if status == "review" else 1 if "no-match" else 2,  # review first
    -r["confidence_pct"],                         # highest confidence first
    r["source_field"].lower(),                    # alpha tie-breaker
))
```

---

## 6. UX Specification

### 6.1 Panel Placement

The **Resolution Story** panel is inserted into the preflight modal **between** the encoding findings section and the existing Salesforce match table. The existing table is **preserved** but collapsed by default when a resolution story is available.

```
[Gate Badge]
[Encoding Findings]
[Resolution Story Panel]  ← NEW
[SF Match Table]           ← existing, collapsed by default
[Export / Close buttons]
```

### 6.2 Badge System

| Badge | Color (Light / Dark) | Condition |
|---|---|---|
| `Legal Entity` | Blue (`#1565c0` / `#42a5f5`) | Assigned to the `legal_entity_account` |
| `Counterparty` | Teal (`#00796b` / `#4db6ac`) | Assigned to each `counterparty_account` |
| `Multi-Counterparty` | Amber (`#f57f17` / `#ffd54f`) | Shown when `counterparties.length > 1` |
| `Manual Confirmation Required` | Red (`#c62828` / `#ef5350`) | Shown when `requires_manual_confirmation === true` |
| `Auto-Matched` | Green (`#2e7d32` / `#66bb6a`) | Shown when legal entity has `match` status |

Badges are rendered as inline chips next to entity names in Section A.

### 6.3 Expand/Collapse Behavior

- **Section A–D** (Resolution Story): Expanded by default. Not individually collapsible — they form a single narrative flow.
- **Full Match Table**: Collapsed by default. Toggle label: "Show Full Match Table" / "Hide Full Match Table". State NOT persisted to localStorage (always starts collapsed on fresh load).
- **Per-row details** in the full table: The existing Debug toggle continues to show `source_type` and `scoring_breakdown`. No changes.
- **Hidden candidates**: Remain in a collapsible "Low-Signal Candidates" section within the full table.

### 6.4 Empty / Low-Confidence / Error States

| State | Rendering |
|---|---|
| No candidates extracted | Section A shows "No account candidates could be extracted from this document." Sections B–D hidden. Full table shows empty state. |
| All candidates below display threshold | Section A shows "No candidates met the confidence threshold for display." Full table hidden section shows all candidates. |
| All candidates in `no-match` status | Section A shows "No confident matches found." Section D shows "Manual lookup required — no automatic resolution available." |
| Resolver not available (import error) | Section A shows "Salesforce resolver is not available. Account matching could not be performed." Sections B–D hidden. |
| Error during scoring | Section A shows "An error occurred during account matching. See console for details." Full table shows raw fallback if available. |
| Single `match` candidate, no counterparties | Section A shows legal entity only. Counterparty row shows "— none detected —". Section D shows "No counterparty detected. Verify this is a unilateral document or identify counterparty manually." |

---

## 7. Acceptance Criteria

### Entity Resolution Correctness

| # | Criterion | Expected Behavior |
|---|---|---|
| AC-01 | 1888 Records distribution agreement | `legal_entity_account` = "1888 Records" with `match` status. "Distribution", "Trademark", "DELAY", "Image", "Mean" do NOT appear in resolution story entities. |
| AC-02 | Aakriti contract | `legal_entity_account` = "Aakriti" (or closest CSV match). If confidence < 0.65, `requires_manual_confirmation = true`. |
| AC-03 | DSP-heavy document (Spotify/TikTok/Apple Music listed) | DSP names do NOT appear as `legal_entity_account` or `counterparties`. They appear only in the full table with `service_context_penalty` chip and reduced scores. |
| AC-04 | Multi-counterparty agreement | Both counterparties appear in `counterparties[]`. `Multi-Counterparty` badge is shown. |
| AC-05 | Strict label:value extraction | "Account Name: Acme Corp" → `legal_entity_account` with `source_type = strict_label_value` and highest priority. |
| AC-06 | CSV phrase hit | Known account name found in body text → candidate with `source_type = csv_phrase_hit`. |
| AC-07 | Header fallback only | When no label:value or CSV matches exist, header-fallback candidates appear with lower trust and explicit "Header Fallback" indicator. |

### Scoring & Ranking

| # | Criterion | Expected Behavior |
|---|---|---|
| AC-08 | Generic token suppression | Single-token denylist words (distribution, trademark, etc.) are excluded from candidates unless `source_type = strict_label_value`. |
| AC-09 | Generic token status cap | Generic tokens that pass extraction max out at `review` status (never `match`) unless `source_type = strict_label_value`. |
| AC-10 | Source-type sorting | `strict_label_value` candidates always rank above `csv_phrase_hit`, which rank above `header_fallback`, regardless of composite score. |
| AC-11 | Address locality | Address evidence only boosts candidates mentioned within 150-char proximity window. A street address on page 1 does NOT boost a candidate on page 8. |
| AC-12 | Service penalty caps | `strict_label_value` source: service penalty ≤ 0.08. `csv_phrase_hit` source: ≤ 0.15 (unless known DSP). |
| AC-13 | Two-tier context proximity | Strong cues searched in both 60-char and 120-char windows. Weak cues searched only in 60-char window. |

### Narrative Panel

| # | Criterion | Expected Behavior |
|---|---|---|
| AC-14 | Section A renders entity cards | Legal entity and counterparties shown with name, confidence %, badge, and source type indicator. |
| AC-15 | Section B renders reasoning steps | At least one reasoning step per visible candidate. Steps are ordered by extraction priority (P1 → P4). |
| AC-16 | Section C renders agreement type | Agreement type shown with inference source (title, recital, keywords). "Unknown" shown when no inference possible. |
| AC-17 | Section D renders analyst actions | At least one action item when `requires_manual_confirmation = true`. Zero action items only when all entities are `match` status. |
| AC-18 | Full table preserved | Existing SF match table is rendered below the story panel, collapsed by default. All existing functionality (chips, debug toggle, hidden candidates) unchanged. |

### Regression Safety

| # | Criterion | Expected Behavior |
|---|---|---|
| AC-19 | Missing Required / Invalid Picklist rendering | Preflight sections for gate, encoding, page classification render identically to current behavior. No regressions. |
| AC-20 | Mojibake inline highlighting | Corruption samples and mojibake detection in encoding section unchanged. |
| AC-21 | Export functionality | Preflight export (`prep_export_v0`) includes `resolution_story` in output. Existing export fields unchanged. |
| AC-22 | Dark mode | All resolution story elements use CSS variables from `ui/viewer/theme.css`. Light and dark modes render correctly. |
| AC-23 | Empty document handling | Documents with no extractable text show appropriate empty state, not errors or blank panels. |
| AC-24 | Performance | Resolution story assembly adds < 50ms to preflight total time. No additional network requests. |

---

## 8. QA Plan

### 8.1 Role Matrix

| Role | Access to Resolution Story | Expected Usage |
|---|---|---|
| **Analyst** (primary) | Full read access. Can expand/collapse sections. Can view full match table. | Primary consumer. Uses narrative to confirm entity resolution before proceeding. |
| **Verifier** | Full read access (same as analyst in preflight context). | Reviews analyst's entity confirmation decisions. |
| **Admin** | Full read access + Debug toggle. | Calibration review. Can inspect scoring breakdowns. |
| **Sandbox/Demo** | Full read access. Uses mock data. | Testing and demonstration. |

### 8.2 Fixture Matrix (Known PDFs)

| Fixture | Expected Legal Entity | Expected Counterparty | Key Test Points |
|---|---|---|---|
| 1888 Records Distribution Agreement | 1888 Records | (counterparty from recitals) | Noise suppression (Distribution, Trademark, DELAY). Source-type priority. Address locality. |
| Aakriti Contract | Aakriti | (per document) | Low-confidence handling. Manual confirmation flag. |
| DSP-heavy agreement | (non-DSP entity) | (non-DSP entity) | Spotify/TikTok/Apple Music suppressed. Service penalty applied correctly. |
| Multi-party agreement | (first party) | (second party, third party) | Multi-counterparty badge. Multiple entries in `counterparties[]`. |
| Single-page simple contract | (labeled entity) | — | Clean extraction. No noise. No counterparty detected state. |
| Scanned/OCR document (YELLOW gate) | (may be empty) | — | Empty state rendering. Gate color interaction. |
| Amendment document | (amending party) | (amended party) | Agreement type = "amendment". |
| No-text document (RED gate) | — | — | Full empty state. No resolution story panel. |

### 8.3 Determinism Checks

1. **Same input → same output.** Run preflight on the same PDF 3 times. Assert `resolution_story` is byte-identical across runs.
2. **Score reproducibility.** For each fixture, record composite scores. Re-run after code changes. Assert scores unchanged (within rounding tolerance of 0.0001).
3. **Sort stability.** When two candidates have identical `(source_type, status, confidence)`, alpha tie-breaker must produce consistent order.

### 8.4 Regression Checks

1. **Existing 254 tests pass.** No test modifications unless adding new tests.
2. **Smoke test (`scripts/replit_smoke.sh`) passes.** Preview output matches expected baseline.
3. **Encoding section unchanged.** Screenshot comparison of encoding findings before and after.
4. **Page classification unchanged.** Same page-mode assignments for all fixture PDFs.
5. **Export backward-compatible.** `prep_export_v0` JSON includes new `resolution_story` key but all existing keys unchanged.

### 8.5 Smoke Sequence

```
1. Start PDF Proxy workflow
2. Load preflight modal for 1888 Records fixture
3. Verify Section A shows "1888 Records" as Legal Entity with match badge
4. Verify Section B shows ≥ 3 reasoning steps
5. Verify Section C shows "Distribution Agreement"
6. Verify Section D shows appropriate analyst actions
7. Expand Full Match Table — verify all rows present with chips
8. Toggle Debug — verify scoring_breakdown visible
9. Switch to dark mode — verify all elements render correctly
10. Export — verify resolution_story in output JSON
11. Load DSP-heavy fixture — verify Spotify/TikTok suppressed
12. Load scanned document — verify empty/degraded state
```

---

## 9. Clarity Questions (Blocking Only)

| # | Question | Recommendation | Blocking? |
|---|---|---|---|
| CQ-1 | Should recital-party parsing (P1) be implemented in this phase, or deferred to a follow-up? | **Recommend: Defer to P2 phase.** Recital parsing requires regex development and testing against diverse contract formats. The resolution story can launch with P2–P4 sources and add P1 later. The `recital_parties` field should be present in the payload but populated as `[]` initially. | Yes — determines scope of P0 backend work. |
| CQ-2 | Should `legal_entity_account` selection require analyst confirmation before downstream use, or is it purely informational in preflight? | **Recommend: Informational only in V1.** The preflight modal is a read-only preview. Add confirmation buttons in a follow-up phase. Set `requires_manual_confirmation` flag but do not gate any workflow on it yet. | Yes — determines whether UI needs interactive confirm/reject buttons. |
| CQ-3 | Should `agreement_type_guess` be surfaced as a confidence-weighted guess or a deterministic classification? | **Recommend: Confidence-weighted guess.** Use keyword matching with a simple scoring heuristic (title weight > recital weight > body keyword weight). Display with "(inferred)" qualifier. | No — does not change data contract shape. |
| CQ-4 | Should the `resolution_story` field be included in the existing `prep_export_v0` export, or in a new `prep_export_v1` format? | **Recommend: Add to existing `prep_export_v0`.** The field is additive and backward-compatible. Consumers that don't expect it will ignore it. | No — additive change. |

---

## 10. Go/No-Go + Phased Task Plan

### 10.1 Recommendation

**GO** — with CQ-1 resolved as "defer recital parsing to P2" and CQ-2 resolved as "informational only in V1."

The resolution story is a presentation-layer feature built on top of the already-calibrated v2.57 scoring engine. The backend data contract is a lightweight assembly of existing scoring outputs into a narrative structure. The frontend is a new panel that renders alongside the existing table. Risk is low.

### 10.2 Phased Task Plan

#### P0 — Backend Contract + Ranking (Foundation)

| Task ID | Description | Dependencies | Estimate |
|---|---|---|---|
| P0-1 | Implement `build_resolution_story()` in `preflight_engine.py` | None | Core assembly function. Selects `legal_entity_account`, builds `counterparties[]`, generates `reasoning_steps[]` and `analyst_actions[]` from existing `salesforce_match` results. |
| P0-2 | Add `agreement_type_guess` inference | None | Keyword-based heuristic scanning title, recitals, body. Returns one of the canonical types. |
| P0-3 | Add `recital_parties` stub | None | Empty array `[]` in V1. Field present in payload for forward compatibility. |
| P0-4 | Wire `resolution_story` into `run_preflight()` response | P0-1, P0-2, P0-3 | Add `resolution_story` key to return dict after `salesforce_match`. |
| P0-5 | Add per-candidate `recital_party_hit` and `label_value_hit` booleans | P0-1 | Derive from existing `source_type` and (future) recital data. |
| P0-6 | Write unit tests for `build_resolution_story()` | P0-1 through P0-5 | Target: 20+ test cases covering all AC items. |
| P0-7 | Update smoke test baseline | P0-4 | `sf_packet.preview.json` must include `resolution_story`. |

#### P1 — Frontend Narrative + Explainability

| Task ID | Description | Dependencies | Estimate |
|---|---|---|---|
| P1-1 | Build Resolution Story panel HTML/CSS skeleton | P0-4 | Sections A–D with CSS variable integration for dark mode. |
| P1-2 | Render Section A — entity cards with badges | P1-1 | Legal entity, counterparties, business unit, parent account. Badge chip system. |
| P1-3 | Render Section B — reasoning steps | P1-1 | Ordered prose list from `reasoning_steps[]`. |
| P1-4 | Render Section C — agreement type | P1-1 | Single line with inferred type and qualifier. |
| P1-5 | Render Section D — analyst actions | P1-1 | Action items with severity indicators (⚠ / ✓). |
| P1-6 | Collapse existing SF table by default | P1-1 | Add expand/collapse toggle. Preserve all existing table functionality. |
| P1-7 | Implement empty/error state rendering | P1-1 | All states from UX Specification §6.4. |
| P1-8 | Dark mode verification | P1-1 through P1-7 | All new elements use `theme.css` variables. |

#### P2 — Calibration + Polish + Docs/Tests

| Task ID | Description | Dependencies | Estimate |
|---|---|---|---|
| P2-1 | End-to-end QA with fixture matrix | P1-8 | All fixtures from §8.2 tested. |
| P2-2 | Recital-party parsing (P1 priority source) | P0-3 | Parse "by and between", WHEREAS clauses. Populate `recital_parties[]`. Wire into scoring as highest priority. |
| P2-3 | Analyst confirmation UI (interactive) | P1-5 | Confirm/reject buttons on entity cards. State persisted to session. |
| P2-4 | Export integration | P0-4 | `resolution_story` included in `prep_export_v0` output. |
| P2-5 | Update `replit.md` with resolution story architecture | P0-4 | Document new payload shape, rendering logic, and design decisions. |
| P2-6 | Regression test suite expansion | P2-1 | Target: 280+ total tests (current: 254). |

### 10.3 Dependency Graph

```
P0-1 ──┬── P0-4 ──── P1-1 ──┬── P1-2
P0-2 ──┤                    ├── P1-3
P0-3 ──┤                    ├── P1-4
       │                    ├── P1-5
P0-5 ──┘                    ├── P1-6
                             ├── P1-7
P0-6 (parallel)             └── P1-8 ── P2-1
P0-7 (after P0-4)                       P2-2 (can start after P0-3)
                                         P2-3 (after P1-5)
                                         P2-4 (after P0-4)
                                         P2-5 (after P0-4)
                                         P2-6 (after P2-1)
```

### 10.4 Risk Assessment

| Risk | Likelihood | Mitigation |
|---|---|---|
| Recital parsing regex fails on unusual contract formats | Medium | Deferred to P2. Start with simple "by and between" pattern. Iterate. |
| Resolution story assembly adds latency | Low | Assembly is pure in-memory transformation of existing data. No I/O. |
| Dark mode color issues | Low | Use existing `theme.css` variable system. Test during P1-8. |
| Backward compatibility break in export | Low | `resolution_story` is additive. Existing keys unchanged. |
| Analyst confusion from new panel | Medium | Keep existing table available. Panel is supplementary, not replacement. |

---

**END OF CLARITY DOCUMENT**

**GO/NO-GO: GO** — Proceed to implementation with CQ-1 (recital parsing) deferred to P2 and CQ-2 (confirmation buttons) deferred to P2.
