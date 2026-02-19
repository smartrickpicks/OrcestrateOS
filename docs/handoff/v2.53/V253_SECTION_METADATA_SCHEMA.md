# V2.53 Section Metadata Schema Reference

**Date:** 2026-02-14
**Status:** Active
**Location:** `rules/rules_bundle/field_meta.json` → `enrichments.section_metadata`

---

## 1. Overview

Section metadata defines how fields are grouped, ordered, and described within each sheet (e.g., Accounts, Opportunities, Financials). It is consumed by `_orderFieldsBySectionMetadata()` in the viewer to produce structured field groups in the Record Inspector, and by `_getSectionFocusFromMeta()` to provide contextual review guidance.

---

## 2. Top-Level Structure

```json
{
  "enrichments": {
    "section_metadata": {
      "<SheetName>": {
        "section_headers": [ ... ],
        "field_section_map": [ ... ],
        "section_focus": "<string>"
      }
    }
  }
}
```

Each key under `section_metadata` is a sheet name (e.g., `"Accounts"`, `"Opportunities"`).

---

## 3. `section_headers` Array

Each entry defines a section group within the sheet.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `section_key` | string | Yes | Unique identifier for the section within the sheet (e.g., `"core_deal_identity"`) |
| `section_title` | string | Yes | Human-readable section name displayed in the group header (e.g., `"Core Deal Identity"`) |
| `description` | string | No | Optional description shown below the section title |
| `display_order` | number | No | Sort order for sections (lower = first); defaults to array index |

### Example

```json
{
  "section_key": "core_deal_identity",
  "section_title": "Core Deal Identity",
  "description": "Primary fields that establish the deal's identity and parties involved.",
  "display_order": 1
}
```

---

## 4. `field_section_map` Array

Maps individual fields to their parent section and defines the display order within that section.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `field_key` | string | Yes | The field's canonical key (e.g., `"account_name_c"`) |
| `section_key` | string | Yes | References a `section_key` from `section_headers` |
| `question_order` | number | Yes | Sort order within the section (lower = first); must be unique within each section |

### Example

```json
{
  "field_key": "account_name_c",
  "section_key": "core_deal_identity",
  "question_order": 1
}
```

### Constraints

- Every `section_key` in `field_section_map` must reference a valid entry in `section_headers`.
- `question_order` values should be unique within each `section_key` group.
- Fields not present in `field_section_map` are placed in an "Other Fields" group.

---

## 5. `section_focus` String

A prose paragraph describing what the analyst should focus on when reviewing fields in this sheet. Used by `_getSectionFocusFromMeta()` to populate the Section Guidance Card.

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `section_focus` | string | No | Free-text guidance paragraph; rendered as prose (not as a bullet list) |

### Example

```
"section_focus": "Focus on verifying the deal's financial terms match the contract language. Pay attention to payment frequency, advance amounts, and territory splits. Cross-reference royalty rates against the rate card when available."
```

When `section_focus` is present, the guidance card displays it as a readable paragraph with a "From schema" badge. When absent, the card falls back to `config/section_guidance.json` with a "Default guidance" badge.

---

## 6. Consumer Functions

### `_orderFieldsBySectionMetadata(sheetName, record)`

- **Input:** Sheet name and record object
- **Output:** Array of group objects `{ name, type, section_key, description, fields[] }`
- **Behavior:**
  - Reads `section_metadata[sheetName]` from `rulesBundleCache.fieldMeta.enrichments`
  - Creates groups from `section_headers`, populates with matched fields from `field_section_map`
  - Sorts fields within groups by `question_order`
  - Unmapped fields go to "Other Fields" group
  - Returns `null` if no section_metadata exists for the sheet (triggers legacy grouping)

### `_getSectionFocusFromMeta(sheetName)`

- **Input:** Sheet name
- **Output:** Guidance object or `null`
- **Behavior:**
  - Returns `{ section_label, what_to_look_for: [], _focus_prose: <text>, common_failure_modes: [], _source: 'section_metadata' }`
  - Returns `null` if `section_focus` is empty or missing (triggers JSON fallback)

### `renderSectionGuidanceCard(record, container)`

- **Input:** Record object and DOM container
- **Behavior:**
  - Calls `_getSectionFocusFromMeta()` first, falls back to JSON config
  - Renders collapsible guidance card with source badge
  - Shows prose paragraph for `_focus_prose`, bullet list for `what_to_look_for` array items

---

## 7. QA Validation

The `section_meta` QA suite (`QARunner.runSuite('section_meta')`) validates:

1. `rulesBundleCache.fieldMeta` is loaded
2. `section_metadata` contains at least one sheet
3. Per sheet:
   - `section_headers` array is non-empty
   - `field_section_map` array is non-empty
   - `section_focus` string is present and non-empty
   - No orphaned field mappings (all `section_key` refs resolve to a header)
4. Fallback: `_getSectionMetadata('NONEXISTENT_SHEET')` returns `null`

---

## 8. Complete Example

```json
{
  "enrichments": {
    "section_metadata": {
      "Opportunities": {
        "section_headers": [
          {
            "section_key": "core_deal_identity",
            "section_title": "Core Deal Identity",
            "description": "Primary fields that establish the deal.",
            "display_order": 1
          },
          {
            "section_key": "financial_terms",
            "section_title": "Financial Terms",
            "description": "Payment, royalty, and advance details.",
            "display_order": 2
          }
        ],
        "field_section_map": [
          { "field_key": "account_name_c", "section_key": "core_deal_identity", "question_order": 1 },
          { "field_key": "opportunity_name_c", "section_key": "core_deal_identity", "question_order": 2 },
          { "field_key": "amount_c", "section_key": "financial_terms", "question_order": 1 },
          { "field_key": "royalty_rate_c", "section_key": "financial_terms", "question_order": 2 }
        ],
        "section_focus": "Verify that the deal's financial terms match the contract language exactly. Pay special attention to payment frequency, advance amounts, and territory-specific splits."
      }
    }
  }
}
```
