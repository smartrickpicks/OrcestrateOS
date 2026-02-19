# V2.56 Field Suggestions UI Upgrade — Acceptance Criteria

## Status: COMPLETE

## Summary
Analyst review mode (SRR Inspector) enhanced with collapsible section headers,
per-section status pills, dark mode fixes, and right-click context menu parity.

## Changes

### 1. Collapsible Section Headers
- Section group headers now toggle open/closed on click
- Chevron indicator (▶/▼) shows collapse state
- Collapse state persisted to localStorage per section key
- Info button and Bulk Verify button have stopPropagation to prevent toggle

### 2. Per-Section Status Pills
Each section header shows inline status counts:
- **todo** (amber) — fields still needing review
- **verified** (green) — verified field count with checkmark
- **RFI** (amber) — fields with Request For Information
- **blocked** (red) — blocked fields with warning icon
- `section-complete` CSS class applied when all fields verified

### 3. Dark Mode Fixes
- Replaced 16 hardcoded `background: #f5f5f5` thead colors with `var(--table-head-bg, var(--bg-2, #f5f5f5))`
- Updated `.srr-file-action-bar` from `#f8fafc` to `var(--bg-2, #f8fafc)`
- Added dark mode overrides for: `.srr-file-action-bar`, `.srr-top-bar`, `.srr-glossary-entry`, `.srr-section-info-modal-body`
- Status pills have proper dark mode variants using semi-transparent backgrounds and neon palette colors
- `.group-section` headers use violet accent in dark mode

### 4. Context-Menu Parity
- Right-click on any field card shows context menu with:
  - **Todo fields**: Verify, Request Info (RFI), Flag/Block
  - **Non-todo fields**: Reset to TODO
  - **All fields**: Select field
- Context menu auto-dismisses on outside click
- Read-only mode suppresses context menu
- Uses existing `.context-menu` CSS class (dark mode already supported)

### 5. CSV-Backed Account Resolver
- `server/resolvers/salesforce.py` upgraded from stub to CSV-backed resolver
- 3-tier matching: exact → token overlap (Jaccard) → edit distance (Levenshtein)
- Thresholds: exact=1.0, fuzzy≥0.6, ambiguous cutoff=0.85
- Max 5 candidates, stable sort by (-score, account_name)
- Provider: `cmg_csv_v1`
- All 16 `test_account_resolver.py` tests pass

## Test Results
- **79 pytest tests**: all passing
- **Smoke test**: passing
- **Export validation**: passing

## Key Files
| File | Change |
|------|--------|
| `ui/viewer/index.html` | Collapsible headers, status pills, dark mode CSS, context menu |
| `server/resolvers/salesforce.py` | CSV-backed resolve_account with 3-tier matching |
| `server/resolvers/account_index.py` | Unchanged — AccountIndex, normalize, tokenize |
| `tests/test_suggestion_engine.py` | Updated stub tests → CSV resolver tests |
| `tests/test_drive_batch_ingest.py` | Added EITHER + get_workspace_role to auth mock |
| `tests/test_drive_export_conventions.py` | Added EITHER + get_workspace_role to auth mock |

## CSS Tokens (Dark Mode)
```css
.srr-sec-pill.attention  → rgba(251,191,36,0.15) / #fbbf24
.srr-sec-pill.verified   → rgba(52,211,153,0.15) / #34d399
.srr-sec-pill.rfi        → rgba(251,191,36,0.15) / #fbbf24
.srr-sec-pill.blocked    → rgba(251,113,133,0.15) / #fb7185
.group-section           → rgba(139,92,246,0.12) / #c4b5fd
```
