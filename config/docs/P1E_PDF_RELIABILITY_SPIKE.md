# P1E PDF Reliability Spike — Strict Deliverable

**Version:** 2.3.5  
**Date:** 2026-02-09  
**Runtime Attestation:** GREEN (27/27)

---

## 1. Failure Taxonomy

| Failure Mode | Root Cause | Detection Method | Severity |
|---|---|---|---|
| **Mojibake (garbled text)** | PDF text layer encoded incorrectly; extraction yields replacement chars (U+FFFD) or high-ratio control characters | `_p1eDetectMojibake`: replacement char ratio > 5% OR control char ratio > 3% | `blocker` |
| **Non-searchable PDF** | Scanned image PDFs without OCR; text extraction returns empty or near-empty pages | `_p1eDetectNonSearchable`: > 80% of pages have empty/minimal text (< 10 chars) | `warning` |
| **Smart quote mismatch** | Source PDF uses typographic quotes (U+201C/U+201D/U+2018/U+2019); cell value uses straight quotes | `_p1eNormalizeForSearch` normalizes both sides before comparison | recovered |
| **Em-dash / NBSP mismatch** | PDF uses em-dash (U+2013) or non-breaking space (U+00A0) vs standard hyphen/space in cell | `_p1eNormalizeForSearch` replaces em-dashes with hyphens and NBSP with spaces | recovered |
| **Whitespace compression** | PDF text has collapsed or expanded whitespace compared to cell value | Variant strategy: both sides normalized to single-space runs | recovered |
| **Non-ASCII residue** | Accented or special characters in cell value not present in PDF text layer | `_p1eAsciiNormalize` strips non-printable/non-ASCII chars for fallback match | recovered |
| **Long value truncation** | PDF text layer truncates or re-wraps very long cell values (> 40 chars) | Substring variant: tries first 40 chars of long values as anchor | recovered |
| **Punctuation noise** | Parentheses, brackets, or other punctuation differs between cell and PDF text | No-punct variant: strips all non-alphanumeric characters before matching | recovered |
| **Refresh churn** | Identical URL+page+search being reloaded into `<object>` on every field click | `srrForcePageNav` compares current `obj.data` against new URL; skips if unchanged | eliminated |

---

## 2. Quick-Fix Matrix

| Symptom | Diagnostic Step | Quick Fix | Escalation |
|---|---|---|---|
| Field click does nothing in PDF | Open browser console, filter `[PDF-RELIABILITY][P1E]` | Check `match_result` log — if all 5 variants failed, value may not exist in PDF | Manual page/search via PDF viewer toolbar |
| PDF shows garbled characters | Call `_p1eShowDiagPanel()` from console | Check `textStatus` — if `mojibake`, document routed to Pre-Flight as `OCR_UNREADABLE` | Re-extract PDF with different encoding or request new PDF from source |
| All pages blank in PDF viewer | Check diag panel `pageCount` and `textStatus` | If `non_searchable`, routed to Pre-Flight as `TEXT_NOT_SEARCHABLE` | Run OCR on source PDF (Tesseract/Adobe) before re-import |
| PDF reloads on every click | Check console for `[P1E] nav_skip` logs | If no skip logs, URLs may differ — check `_p1eDiagState.sourceUrl` | Verify proxy is returning stable blob URLs |
| Match found on wrong page | Check `match_result` log for `matchPages` array | Multiple pages may contain the value — first match is used | Add page hints to field_meta.json for disambiguation |
| Diag panel won't open | Run `_p1eShowDiagPanel()` in console | Check for JS errors; panel requires `#p1e-diag-panel` element | Verify P1E CSS was applied (look for `.p1e-diag-panel` style) |

---

## 3. Anchor Search Variant Samples

### Variant 1: Trimmed (whitespace strip)
```
Input:  "  Hello World  "
Output: "Hello World"
Use:    Removes leading/trailing whitespace from cell values
```

### Variant 2: Normalized (typography fix)
```
Input:  "\u201CHello\u201D \u2018world\u2019 \u2013 test\u00A0space"
Output: '"Hello" \'world\' - test space'
Use:    Smart quotes → straight, em-dash → hyphen, NBSP → space
```

### Variant 3: ASCII-only (non-ASCII strip)
```
Input:  "Caf\u00e9 \u201Ctest\u201D value"
Output: 'Caf "test" value'
Use:    Strips combining marks and extended Unicode, keeps ASCII printable
```

### Variant 4: Substring (long value fallback)
```
Input:  "This contract is between Alpha Corp Ltd and Beta Corp Inc for the provision of services under Agreement No. 12345"
Output: "This contract is between Alpha Corp Ltd " (first 40 chars)
Use:    For values > 40 chars, tries first 40 chars as anchor
```

### Variant 5: No-punctuation (stripped)
```
Input:  "Amount: $1,000.00 (USD)"
Output: "Amount 100000 USD"
Use:    Removes all non-alphanumeric characters for fuzzy matching
```

### Resolution Order
Variants are tried sequentially. First match wins. If all 5 fail, a `[P1E] match_failed` log is emitted with all attempted variants listed.

---

## 4. Pre-Flight Signal Mapping

| Signal Type | Severity | Trigger Condition | Triage Bucket | User-Visible Label |
|---|---|---|---|---|
| `OCR_UNREADABLE` | `blocker` | `_p1eDetectMojibake` returns `isMojibake: true` (replacement chars > 5% or control chars > 3%) | Pre-Flight | "PDF text is garbled or unreadable" |
| `TEXT_NOT_SEARCHABLE` | `warning` | `_p1eDetectNonSearchable` returns `nonSearchable: true` (> 80% pages empty) | Pre-Flight | "PDF has no searchable text" |

### Deduplication
Signals are keyed by `contract_key + signal_type`. Duplicate routing attempts are silently dropped. Log: `[P1E] preflight_dedup_skipped`.

### Integration with P1D
P1E Pre-Flight items appear in P1D's contract-grouped view. Items group under the contract's file_name with domain hint. Contract section chips show "PDF" for document-level items.

---

## 5. Cache Diagnostics Panel

### Access
- Console: `_p1eShowDiagPanel()` / `_p1eHideDiagPanel()` / `_p1eToggleDiagPanel()`
- Panel ID: `#p1e-diag-panel`

### Fields Displayed
| Field | Source | Description |
|---|---|---|
| Source URL | `_p1eDiagState.sourceUrl` | Original PDF URL before proxy fetch |
| Cache Key | `_p1eDiagState.cacheKey` | Key used for blob URL cache lookup |
| Last Loaded | `_p1eDiagState.lastLoaded` | Timestamp of last successful PDF load |
| Text Status | `_p1eDiagState.textStatus` | `ok` / `mojibake` / `non_searchable` / `pending` |
| Page Count | `_p1eDiagState.pageCount` | Number of pages with extracted text |
| Match Attempts | `_p1eDiagState.matchAttempts` | Array of recent match attempt logs |

---

## 6. Migration Recommendation

### Current Architecture
- Native `<object>` embed for PDF rendering
- Server-side text extraction via PyMuPDF (FastAPI proxy at `/api/pdf-text`)
- Client-side anchor matching against extracted text
- Blob URL caching for fetched PDFs

### Recommended Path (No Change Required)
The current architecture is sufficient for the governance use case:
- PyMuPDF extraction quality is high for digitally-created PDFs
- The 5-variant matching strategy handles most encoding/formatting mismatches
- Pre-Flight routing catches genuinely unreadable documents early
- Refresh churn elimination reduces perceived latency

### Future Considerations
1. **OCR integration**: For high volumes of scanned PDFs, consider adding Tesseract OCR as a fallback in the FastAPI proxy when PyMuPDF returns empty text
2. **pdf.js migration**: If interactive highlighting (beyond page navigation) becomes required, consider migrating from `<object>` to pdf.js for programmatic text layer access
3. **Server-side matching**: If client-side matching latency becomes an issue with very large PDFs, move variant matching to the server

---

## 7. Runtime Attestation

```
P1E GREEN (27/27)
├── A1  Cold load: no JS errors
├── A2  All P1E functions registered (11/11)
├── A3  Diagnostics panel DOM exists
├── A4  Normalization: smart quotes → plain
├── A5  ASCII normalize: strips extended chars
├── A6  Mojibake detection: replacement chars
├── A7  Non-searchable detection: empty pages
├── A8  Search variants generation (≥3)
├── A9  Match: exact
├── A10 Match: normalized (smart quotes)
├── A11 Match: whitespace normalization
├── A12 Match: substring fallback
├── A13 Match: no false positives
├── A14 Pre-Flight routing: OCR_UNREADABLE
├── A15 Pre-Flight deduplication
├── A16 Pre-Flight routing: TEXT_NOT_SEARCHABLE
├── A17 Diagnostics panel toggle
├── A18 Refresh churn skip
├── A19 Console log prefix verification
├── A20 Regression: P0.2.2 (13/13)
├── A21 Regression: P1 (10/10)
├── A22 Regression: Calibration (8/8)
├── A23 Regression: P0.8 (10/10)
├── A24 Regression: P0.9 (10/10)
├── A25 Regression: P1A (12/12)
├── A26 Regression: P1C
└── A27 Regression: P1D
```

---

## 8. Files Modified

| File | Change |
|---|---|
| `ui/viewer/index.html` | P1E edits (CSS, helpers, highlight replacement, nav optimization, diag panel) |
| `scripts/p1e_delta.py` | Delta application script (5 edits: E1-E5) |
| `scripts/p1e_runtime_validation.py` | Runtime validation (27 checks) |
| `docs/P1E_PDF_RELIABILITY_SPIKE.md` | This deliverable |
| `replit.md` | Updated with P1E documentation |
