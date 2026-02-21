# V2.55.1 — Verifier Org View UI Polish: Clarity Document

**Status:** Implemented (doc-only — no code changes in this phase)  
**Date:** 2026-02-17  
**Scope:** UI-only polish specification for `#/verifier-org` — layout, visual hierarchy, readability, workflow speed  
**Depends on:** V2.55 (VUI-01 through VUI-05 complete, hotfix applied)  
**Hard constraints:** No backend/API changes. No route changes. Additive refinements only. Dark mode preserved.  
**Output:** This document only. Code changes deferred to implementation phase per task list in Section 9.

---

## 1. Audit Snapshot (Current UI Pain Points)

### 1.1 KPI Strip Readability / Click Affordance

| Issue | File / Line | Severity |
|-------|-------------|----------|
| KPI cards lack visual affordance that they are clickable — no pointer cursor text hint, no hover-lift, no "click to filter" subtitle | `index.html:39346–39375` (vorgRenderKpi fn) | P1 |
| Active KPI card only gains a blue outline ring; no fill/bg change to signal "this filter is active" | `index.html:376` (CSS `.vorg-kpi.vorg-kpi-active`) | P1 |
| "Total" card has `cursor:default` but visually identical to clickable cards — confusing parity | `index.html:39346` (vorgRenderKpi inline style) | P2 |
| KPI value uses `2em` font-size without `font-variant-numeric: tabular-nums` — counter widths shift on update | `index.html:39346` (vorgRenderKpi inline style) | P2 |
| No unit hint ("items") below count — verifier must infer what "42" means | `index.html:39346` (vorgRenderKpi fn) | P2 |

### 1.2 Filter Bar Density and Discoverability

| Issue | File / Line | Severity |
|-------|-------------|----------|
| Filter bar uses inline styles with hard-coded padding (`10px 16px`) — cramped on narrow viewports | `index.html:4645` | P1 |
| "Clear" button visually identical to filter selects — low discoverability for reset action | `index.html:4661` | P2 |
| No "result count" label next to filter info span when no filters active — shows raw number without context | `index.html:4660` | P2 |
| Filter dropdowns lack `aria-label` for screen reader identification | `index.html:4647,4654` | P1 |
| No visual badge/chip showing active filters when scrolled past filter bar | N/A (missing) | P3 |

### 1.3 Batch Table Scanning Speed

| Issue | File / Line | Severity |
|-------|-------------|----------|
| No zebra striping on table rows — difficult to track across wide tables | `index.html:379–380` (CSS `.vorg-batch-table tbody tr:hover` only) | P1 |
| No visual distinction for "selected/drilled-into" batch row — user loses context after clicking | `index.html:39496+` (vorgRenderBatchTable fn) | P1 |
| Column headers lack sort affordance (no arrows/icons indicating sortability) | `index.html:4668–4677` | P3 |
| "Health" column shows a bare dot with no text label — meaning not self-evident | `index.html:39249–39252` (_vorgHealthDot) | P2 |
| Pending/Clarify/Resolved columns show raw numbers with no color coding — easy to miss non-zero values | `index.html:39520–39525` | P1 |

### 1.4 Drilldown Table Action Clarity

| Issue | File / Line | Severity |
|-------|-------------|----------|
| Approve and Reject buttons are the same size/weight — destructive action (Reject) not visually differentiated | `index.html:387–392` (CSS `.vorg-action-btn-*`) | P1 |
| "Return" button for RFIs uses reject styling (red) — misleading, as returning is not a destructive action | `index.html:39595` (vorgRenderDrilldown, RFI action row) | P1 |
| No confirmation step for Reject — one-click destructive action | `index.html:39619` (vorgAction fn) | P2 |
| Action column wraps awkwardly on narrow widths despite `white-space:nowrap` on td | `index.html:39612` (drilldown row render) | P2 |
| No disabled/loading state on buttons during async action — double-click risk | `index.html:39619` (vorgAction fn) | P1 |

### 1.5 Empty / Loading / Error State Quality

| Issue | File / Line | Severity |
|-------|-------------|----------|
| Loading state is plain text "Loading operations data..." — no spinner or skeleton | `index.html:4641` | P2 |
| Empty state lacks an icon or illustration — just text | `index.html:4642` | P3 |
| Error banner has retry button but no auto-dismiss or timeout | `index.html:39340–39345` | P3 |
| No per-table empty state differentiation (batch table vs drilldown) — both use generic text | `index.html:39515, 39578` | P2 |

### 1.6 Mobile / Tablet Behavior

| Issue | File / Line | Severity |
|-------|-------------|----------|
| KPI strip uses `flex:1;min-width:120px` — wraps to 2 rows on tablet, 5 rows on mobile | `index.html:39369` | P1 |
| Batch table and drilldown table overflow-x scroll but have no scroll indicator | `index.html:4665` | P2 |
| Filter bar wraps items but with no priority — selects and button can end up on separate rows | `index.html:4645` | P2 |
| "Back to all batches" button in drilldown may wrap below title on narrow widths | `index.html:4686` | P2 |

---

## 2. UX Targets (Explicit Before/After)

### 2.1 Summary Strip Hierarchy

| Aspect | Before | After |
|--------|--------|-------|
| Count display | Bare number, no unit | Number + "items" subtitle |
| Click affordance | Cursor pointer only | Pointer + "Click to filter" hint on hover + slight scale-up (1.02) |
| Active state | Blue outline ring only | Blue outline ring + tinted background fill (`var(--accent-bg)`) |
| Total card | Same visual weight as clickable cards | Muted background, no hover effect, "Total" label bolded |
| Number alignment | Proportional figures | `font-variant-numeric: tabular-nums` for stable widths |

### 2.2 Filter Bar Structure

| Aspect | Before | After |
|--------|--------|-------|
| Layout | Inline flex with loose spacing | Grouped: [Label + Selects] gap [Info + Clear] with `margin-left:auto` on info |
| Clear button | Ghost button, blends with selects | Underlined text link style ("Clear all") for lower visual weight |
| Result count | Raw number or "Showing X of Y" | Always visible: "12 items" (no filter) / "Showing 5 of 12" (filtered) with filter icon |
| Active filter indicator | None | Small colored dot on select border when non-default value selected |
| Accessibility | No aria-labels | `aria-label="Filter by status"` and `aria-label="Filter by type"` on selects |

### 2.3 Batch Table Visual Rhythm

| Aspect | Before | After |
|--------|--------|-------|
| Row striping | None | Alternating `var(--table-row-alt, rgba(0,0,0,0.02))` on even rows |
| Row height | 42px (10px padding) | 44px (12px vertical padding) for touch friendliness |
| Hover state | Background change only | Background change + left border accent (3px `var(--accent-bright)`) |
| Selected row | No visual state | Persistent highlighted background until drilldown exits |
| Count columns | Plain text numbers | Non-zero counts get colored badge: pending=amber, clarify=blue, resolved=green |

### 2.4 Age/Health Semantic Indicators

| Aspect | Before | After |
|--------|--------|-------|
| Health dot | Bare 10px circle, tooltip only | Dot + text label: "Fresh" / "Aging" / "Stale" beside dot |
| Age column | Text with color | Text with color + matching background pill for emphasis |
| Consistency | Green/amber/red from `_vorgAgeColor` | Same tokens, extended: `--ok`/`--warn`/`--bad` with matching `-bg` variants |
| Dark mode | Colors render but low contrast | Dark mode uses `--neon-ok`/`--neon-warn`/`--neon-bad` for sufficient contrast |

### 2.5 Drilldown Actions

| Aspect | Before | After |
|--------|--------|-------|
| Button grouping | All buttons inline, same size | Primary action (Approve/Resolve) visually heavier (filled bg); secondary (Reject/Return) outline only |
| Destructive action | Same styling as approve | Reject: red outline + red text; requires `title="This cannot be undone"` |
| RFI Return | Red (reject) styling | Amber/neutral styling — Return is non-destructive |
| Loading state | None | Button shows spinner + disabled during async action |
| Button spacing | Single space character | 6px gap via flexbox wrapper |

### 2.6 Sticky Affordances

| Element | Sticky? | Rationale |
|---------|---------|-----------|
| Page header | No | Short header, not worth screen real estate cost |
| KPI strip | No | Same — scrolling past KPIs is acceptable |
| Filter bar | Yes (sticky) | Filters must remain accessible during batch table scrolling |
| Batch table header | Yes (sticky within scroll container) | Column headers needed for reference while scanning rows |
| Drilldown "Back" button | Yes (sticky at top of drilldown) | Exit affordance must remain visible |

---

## 3. Visual System Contract

### 3.1 CSS Variable Usage

All new styles MUST use existing CSS custom properties from `ui/viewer/theme.css`. No hard-coded colors permitted.

| Purpose | Light Token | Dark Token | Fallback |
|---------|------------|------------|----------|
| KPI active bg | `var(--accent-bg)` | `var(--accent-bg)` | `rgba(21,101,192,0.06)` |
| Table row alt | `var(--table-row-alt)` | `var(--table-row-alt)` | `rgba(0,0,0,0.02)` |
| Table row hover | `var(--bg-3)` | `var(--bg-3)` | `#eef1f5` |
| Badge pending | `var(--warn-bg)` / `var(--warn)` | inherited | `#fff3e0` / `#e65100` |
| Badge clarify | `var(--info-bg)` / `var(--info)` | inherited | `#e3f2fd` / `#1565c0` |
| Badge resolved | `var(--ok-bg)` / `var(--ok)` | inherited | `#e8f5e9` / `#2e7d32` |
| Button loading | `var(--text-muted)` | inherited | `#999` |
| Focus ring | `var(--accent-bright)` | `var(--accent-bright)` | `#1565c0` |

### 3.2 Typography Scale

| Element | Size | Weight | Line Height | Token |
|---------|------|--------|-------------|-------|
| Page title | 1.5em | 600 | 1.2 | `var(--text-1)` |
| Page subtitle | 0.9em | 400 | 1.4 | `var(--text-secondary)` |
| KPI count | 2em | 700 | 1.1 | `var(--text-1)` |
| KPI label | 0.82em | 500 | 1.3 | `var(--text-secondary)` |
| Table header | 0.82em | 600 | 1.2 | `var(--text-secondary)`, uppercase |
| Table cell | 0.9em | 400 | 1.3 | `var(--text-1)` |
| Badge text | 0.78em | 600 | 1 | Per-badge token |
| Filter label | 0.85em | 400 | 1.3 | `var(--text-secondary)` |
| Action button | 0.8em | 500 | 1.2 | Per-variant token |

### 3.3 Spacing Scale

| Context | Value | Usage |
|---------|-------|-------|
| Section gap | 20px | Between KPI strip, filter bar, batch table, drilldown |
| KPI card padding | 16px | Internal padding |
| KPI gap | 12px | Between KPI cards |
| Table cell padding | 12px vert, 12px horiz | Standard cell spacing |
| Filter bar padding | 10px 16px | Internal, flex-wrap gap 12px |
| Action button padding | 4px 10px | Compact buttons |
| Action button gap | 6px | Between action buttons (flex gap) |

### 3.4 Badge / Button Variants

| Variant | Background | Text | Border | Usage |
|---------|-----------|------|--------|-------|
| `.vorg-badge-patch` | `var(--info-bg)` | `var(--info)` | none | Patch type indicator |
| `.vorg-badge-rfi` | `var(--warn-bg)` | `var(--warn)` | none | RFI type indicator |
| `.vorg-badge-correction` | `var(--ok-bg)` | `var(--ok)` | none | Correction type indicator |
| `.vorg-badge-source` | `var(--chip-bg)` | `var(--chip-text)` | `var(--chip-border)` | Source badge (upload/drive) |
| `.vorg-action-btn-approve` | transparent → fill on hover | `var(--ok)` | `var(--ok-border)` | Approve / Resolve |
| `.vorg-action-btn-reject` | transparent | `var(--bad)` | `var(--bad-border)` | Reject (destructive) |
| `.vorg-action-btn-return` (NEW) | transparent | `var(--warn)` | `var(--warn-border)` | RFI Return (non-destructive) |
| `.vorg-count-badge` (NEW) | per-status bg | per-status text | none | Inline count badge in batch table |

### 3.5 Accessibility Targets

| Requirement | Target | Method |
|-------------|--------|--------|
| Color contrast (text) | WCAG AA (4.5:1 minimum) | All text tokens tested in light + dark |
| Color contrast (large text / badges) | WCAG AA (3:1 minimum) | Badge colors against their backgrounds |
| Focus visibility | 2px outline ring, `var(--accent-bright)` | `:focus-visible` on all interactive elements |
| Keyboard order | Logical tab sequence: KPI strip → filters → batch table → drilldown | Native DOM order (already correct) |
| Screen reader | `aria-label` on filter selects, `role="status"` on filter info | Added to HTML |
| Motion | `prefers-reduced-motion` disables hover transitions | Media query wrapping transitions |

---

## 4. Interaction Contract

### 4.1 KPI Click Behavior

| Trigger | Effect |
|---------|--------|
| Click clickable KPI (Pending/Clarify/Sent to Admin/Resolved) | Toggle filter: if already active, clear; otherwise set as active status filter |
| Click active KPI (second click) | Clear status filter, return to "all" |
| Click "Total" card | No action (non-interactive) |
| KPI active state | Blue ring + tinted bg; filter-status dropdown synced; URL hash updated with `?status=X` |
| Keyboard | KPI cards receive focus via tab; Enter/Space activates click |

### 4.2 Filter Behavior + URL Hash Sync

| Action | URL Update | UI Sync |
|--------|-----------|---------|
| Select status filter | `#/verifier-org?status=pending` | KPI strip highlights matching card |
| Select type filter | `#/verifier-org?type=rfi` | Result count updates |
| Clear all filters | `#/verifier-org` | KPI strip clears active states, selects reset |
| Page load with hash params | Parse `?status=X&type=Y&batch=Z` | Restore filter state, scroll to drilldown if batch present |
| Role switch | Full reload via `vorgLoadData()`; URL preserved | KPI counts refresh, filters reapplied |

### 4.3 Drilldown Entry / Exit Behavior

| Trigger | Effect |
|---------|--------|
| Click batch row in table | Batch table hides, drilldown table shows with batch items; URL gets `?batch=bat_X` |
| Click "Back to all batches" | Drilldown hides, batch table shows; `?batch=` removed from URL |
| Clear filters while in drilldown | Exit drilldown + clear all filters |
| Role switch while in drilldown | Stay in drilldown, reload data for new role |

### 4.4 Role-Switch Refresh Behavior

| Scenario | Expected Behavior |
|----------|-------------------|
| Sandbox: switch analyst → verifier | Page becomes visible; `vorgLoadData()` fires with `X-Sandbox-Mode: true`, `X-Effective-Role: verifier` |
| Sandbox: switch verifier → admin | Data reloads; analyst workload panel becomes visible (future panel) |
| Sandbox: switch verifier → analyst | Navigation redirects away from `#/verifier-org` (RBAC guard) |
| Live: role matches verifier/admin | Standard load, no sandbox headers |

---

## 5. Mismatch Register

| ID | Issue | File / Line | Severity | Proposed Fix |
|----|-------|-------------|----------|-------------|
| MM-01 | KPI cards use inline styles instead of CSS class for layout | `index.html:39346` (vorgRenderKpi) | P1 | Extract inline `style=` to `.vorg-kpi` class properties; keep dynamic values (active state) in JS |
| MM-02 | Batch table row hover exists but no zebra/alt-row styling | `index.html:379–380` (CSS block) | P1 | Add `#vorg-batch-table tbody tr:nth-child(even) { background: var(--table-row-alt) }` |
| MM-03 | RFI "Return" button uses `.vorg-action-btn-reject` (red) styling | `index.html:39595` (vorgRenderDrilldown) | P1 | Create `.vorg-action-btn-return` with `var(--warn)` color; apply to Return buttons |
| MM-04 | No loading/disabled state on action buttons during async | `index.html:39619` (vorgAction) | P1 | Add `disabled` attribute + spinner class during Promise execution; re-enable on settle |
| MM-05 | Filter selects lack `aria-label` | `index.html:4647, 4654` (HTML) | P1 | Add `aria-label="Filter by status"` and `aria-label="Filter by type"` |
| MM-06 | Health dot has no text label — meaning requires tooltip hover | `index.html:39249` (_vorgHealthDot) | P2 | Add text label after dot: "Fresh" / "Aging" / "Stale" |
| MM-07 | KPI count numbers shift width on update (proportional figures) | `index.html:39346` (vorgRenderKpi inline) | P2 | Add `font-variant-numeric: tabular-nums` to `.kpi-value` |
| MM-08 | Pending/Clarify/Resolved counts in batch table are plain text | `index.html:39496` (vorgRenderBatchTable) | P2 | Wrap non-zero values in `.vorg-count-badge` with status-appropriate colors |
| MM-09 | No scroll indicator on horizontal-scroll table containers | `index.html:4665` (HTML wrapper) | P2 | Add gradient fade on right edge when scrollable content is clipped |
| MM-10 | "Total" KPI card visually identical to clickable cards | `index.html:39346` (vorgRenderKpi) | P2 | Add `.vorg-kpi-static` class with muted bg and `cursor:default` |
| MM-11 | Loading state is plain text, no spinner | `index.html:4641` (HTML) | P2 | Add CSS spinner animation inline or `.vorg-spinner` class |
| MM-12 | Filter bar not sticky during scroll | `index.html:4645` (HTML) | P3 | Add `position:sticky;top:0;z-index:10` to `#vorg-filters` |

---

## 6. Acceptance Criteria (Pass/Fail Checklist)

| # | Criterion | Pass Condition |
|---|-----------|----------------|
| AC-01 | KPI cards show "items" subtitle below count | All 5 KPI cards display count + "items" label |
| AC-02 | Clickable KPI cards show pointer cursor and hover scale | Hover over Pending card → cursor:pointer, slight lift/scale |
| AC-03 | Active KPI card has tinted background fill + blue ring | Click Pending → card gets blue ring + accent-bg fill |
| AC-04 | Total KPI card is visually muted and non-clickable | Total card has muted bg, no hover effect, cursor:default |
| AC-05 | KPI count numbers use tabular-nums (stable widths) | Values don't shift horizontally as digits change |
| AC-06 | Batch table has zebra-striped rows | Even rows have subtle alt background |
| AC-07 | Batch table hovered row shows left accent border | Hover a row → 3px blue left border appears |
| AC-08 | Non-zero Pending/Clarify counts in batch table are color-badged | Pending=3 shows amber badge; Clarify=2 shows blue badge |
| AC-09 | Health column shows dot + text label ("Fresh"/"Aging"/"Stale") | Each batch row health shows dot + word |
| AC-10 | RFI "Return" button uses amber/neutral styling, not red | Return button is amber-toned, distinct from Reject |
| AC-11 | Action buttons show disabled+spinner state during async | Click Approve → button grays out with spinner until response |
| AC-12 | Filter selects have `aria-label` attributes | Inspect DOM → `aria-label="Filter by status"` present |
| AC-13 | Filter bar is sticky when scrolling batch table | Scroll down → filter bar stays pinned at top |
| AC-14 | Dark mode: all new styles render with correct dark tokens | Toggle dark mode → no hard-coded colors, no contrast failures |
| AC-15 | Dark mode: KPI active state uses proper dark accent bg | Active KPI in dark mode shows tinted bg without white flash |
| AC-16 | Narrow viewport (≤768px): KPI strip wraps to 2 rows max | Resize to 768px → KPIs wrap cleanly, no 5-row stack |
| AC-17 | Narrow viewport: batch table scrolls horizontally with fade indicator | Resize → table scrollable, gradient on right edge hints at overflow |
| AC-18 | All existing actions (Approve/Reject/Resolve/Return) still function | Exercise each action type → toast confirms, state updates, version bumps |
| AC-19 | URL state sync preserved for all filter combinations | Apply status+type filter → URL updates; refresh page → filters restored |
| AC-20 | Role-switch from verifier-org triggers data reload | Switch role in sandbox → console shows `[OpsView] Refreshing Org View` |

---

## 7. QA Plan

### 7.1 Manual Test Matrix

| # | Scenario | Role | Mode | Steps | Expected Outcome |
|---|----------|------|------|-------|-----------------|
| QA-01 | KPI strip polish | Verifier | Live | Navigate to #/verifier-org | KPI cards show counts + "items" label; hover shows lift; click filters |
| QA-02 | KPI active state | Verifier | Live | Click "Pending" KPI | Card gets blue ring + accent bg; table filters to pending |
| QA-03 | Total card non-interactive | Verifier | Live | Hover/click Total card | No cursor change, no hover effect, no filter applied |
| QA-04 | Batch table zebra | Verifier | Live | Open org view with 3+ batches | Even rows have subtle alt background |
| QA-05 | Batch table count badges | Verifier | Live | View batches with non-zero pending/clarify | Non-zero counts shown as colored badges |
| QA-06 | Health dot + label | Verifier | Live | View batches with varied ages | Dot + "Fresh"/"Aging"/"Stale" label visible |
| QA-07 | RFI Return styling | Verifier | Live | Open batch drilldown with RFI item | Return button is amber, distinct from red Reject |
| QA-08 | Action button loading | Verifier | Live | Click Approve on patch | Button disables with spinner; re-enables after response |
| QA-09 | Filter bar sticky | Verifier | Live | Scroll down with 10+ batches | Filter bar pins to top of page |
| QA-10 | Dark mode full pass | Admin | Live | Toggle dark mode, visit all vorg elements | All elements render with dark tokens, no white flashes |
| QA-11 | Sandbox verifier simulation | Admin | Sandbox | Switch to verifier role, visit org view | Data loads with sandbox headers; all polish visible |
| QA-12 | Sandbox admin simulation | Admin | Sandbox | Stay as admin, visit org view | Same data + admin-level visibility |
| QA-13 | Narrow viewport (768px) | Verifier | Live | Resize browser to 768px width | KPI wraps to 2 rows; table scrolls; filter bar wraps cleanly |
| QA-14 | Narrow viewport (480px) | Verifier | Live | Resize to 480px | KPI cards stack; table horizontally scrollable; actions accessible |

### 7.2 Smoke Steps

1. Navigate to `#/verifier-org` as verifier → page loads, KPI strip + batch table visible
2. Click "Pending" KPI → batch table filters, KPI highlighted, URL updates
3. Click a batch row → drilldown opens with items
4. Click "Approve" on a patch → button shows loading state, toast confirms
5. Click "Back to all batches" → batch table returns
6. Toggle dark mode → all elements render correctly
7. Resize to 768px → layout adapts without breakage

### 7.3 Regression Checks

| Check | Method | Expected |
|-------|--------|----------|
| Patch approve/reject still works | Click Approve in drilldown | Toast "Patch Verifier Approved", version bumps |
| RFI resolve/return still works | Click Resolve/Return on RFI | Correct status transition, toast |
| Correction approve/reject still works | Click Approve on correction | Toast, state update |
| URL state sync intact | Apply filters, refresh page | Filters restored from URL |
| Role switch refresh intact | Switch role while on verifier-org | Console log confirms reload |
| Empty state rendering | Load with no data | "No batches with active items" message |
| Error state rendering | Simulate server error | Red banner with retry button |

---

## 8. Clarity Questions (Blocking Only)

| # | Question | Impact | Recommendation |
|---|----------|--------|----------------|
| CQ-01 | Should the filter bar be sticky or scroll with content? | Layout behavior at scale (many batches) | **Recommend sticky** — verifiers need filter access while scanning. Low implementation cost. |
| CQ-02 | Should Reject actions require a confirmation dialog? | UX safety vs. workflow speed trade-off | **Recommend no dialog for V2.55.1** — action is reversible in governance model (version history). Add in V2.56 if requested. |
| CQ-03 | Should KPI strip include a "Blocked" counter (from batch health)? | Requires batch health fetch which is not currently wired | **Recommend defer to V2.56** — current 5-KPI layout (Pending/Clarify/Sent to Admin/Resolved/Total) is sufficient. Blocked indicator can be added when batch health endpoint is integrated. |
| CQ-04 | Should batch table support column sorting? | Scan speed for verifiers with many batches | **Recommend defer to V2.56** — current client-side data is small enough. Add sort when > 50 batches becomes realistic. |
| CQ-05 | Should the "items" subtitle on KPI cards say "items" or the specific type count breakdown (e.g., "12 patches, 3 RFIs")? | Information density vs. clarity | **Recommend "items"** for simplicity. Type breakdown is available in the filter bar and batch table. |

---

## 9. Go/No-Go

**Verdict: GO**

All items are UI-only CSS + JS refinements within `ui/viewer/index.html`. No backend changes, no API modifications, no route additions. Dark mode support is maintained via existing CSS custom properties. All changes are additive and non-breaking.

### Phased Task List

| Task ID | Description | Priority | Scope |
|---------|-------------|----------|-------|
| VUI-POLISH-01 | KPI strip refinements: tabular-nums, "items" subtitle, active bg fill, Total card muting, hover affordance | P0 | CSS + JS (vorgRenderKpi) |
| VUI-POLISH-02 | Batch table visual rhythm: zebra striping, hover accent border, selected row state | P0 | CSS |
| VUI-POLISH-03 | Count badge system: colored badges for non-zero Pending/Clarify/Resolved in batch table | P1 | CSS + JS (vorgRenderBatchTable) |
| VUI-POLISH-04 | Health label: dot + text label ("Fresh"/"Aging"/"Stale") replacing bare dot | P1 | JS (_vorgHealthDot) |
| VUI-POLISH-05 | Drilldown action buttons: RFI Return amber styling, button gap via flexbox, loading/disabled state | P1 | CSS + JS (vorgAction, render) |
| VUI-POLISH-06 | Filter bar: sticky positioning, aria-labels, Clear link styling, active-filter dots | P1 | CSS + HTML |
| VUI-POLISH-07 | Loading state: CSS spinner replacing plain text | P2 | CSS + HTML |
| VUI-POLISH-08 | Narrow viewport: KPI grid 2-col at ≤768px, scroll fade on tables | P2 | CSS media queries |
| VUI-POLISH-09 | Accessibility pass: focus-visible rings, prefers-reduced-motion, keyboard nav | P2 | CSS |
| VUI-POLISH-10 | Dark mode validation: verify all new tokens render correctly in Palette B | P2 | CSS + manual test |

---

**Doc path:** `docs/handoff/V2551_VERIFIER_ORG_UI_POLISH_CLARITY.md`

**Section checklist:**
- [x] 1. Audit Snapshot (6 subsections, 28 issues catalogued)
- [x] 2. UX Targets (6 before/after tables)
- [x] 3. Visual System Contract (variables, typography, spacing, badges, accessibility)
- [x] 4. Interaction Contract (KPI, filters, drilldown, role-switch)
- [x] 5. Mismatch Register (12 items with file/line refs, P0–P3 severity)
- [x] 6. Acceptance Criteria (20 criteria covering desktop + narrow-width)
- [x] 7. QA Plan (14 test scenarios, 7 smoke steps, 7 regression checks)
- [x] 8. Clarity Questions (5 blocking questions with recommendations)
- [x] 9. Go/No-Go (GO verdict, 10 phased tasks VUI-POLISH-01..10)
