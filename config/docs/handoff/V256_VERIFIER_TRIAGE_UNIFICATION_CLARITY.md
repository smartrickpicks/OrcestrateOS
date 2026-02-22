# V2.56 — Verifier Triage Unification: Clarity Document

**Status:** Draft — DOC + CLARITY ONLY (no code changes)  
**Date:** 2026-02-17  
**Scope:** Specification for migrating verifier/admin experience from standalone `#/verifier-org` page into the canonical triage information architecture  
**Depends on:** V2.55.1 (verifier org view + UI polish — complete), V2.54.1 (role-scoped queue, custody transitions, drive batch dedupe — complete)

---

## 1. Audit Snapshot

### 1.1 What the Triage Frame Provides Today (Analyst View)

The analyst triage frame (`#page-triage > #analyst-triage-content`, lines 3408–3774) is the canonical workspace for analyst-facing review. It renders these sections in order:

| Section | Container ID | Lines | Purpose |
|---------|-------------|-------|---------|
| **Batch Summary Strip** | `#ta-batch-summary` | 3497–3531 | KPI counters: Contracts, Records, Completed, Needs Review, Pending, Updated timestamp |
| **Contract Summary Table** | `#ta-contract-section` | 3532–3573 | Collapsible table: Contract / Doc Role / Stage / Pre-Flight / Semantic / Patches / Rows / Health. Includes health filter bar (Critical/At Risk/Watch/Healthy). Data from `TriageAnalytics` cache (client-side workbook analysis). |
| **Lane Health Cards** | 3-col grid | 3576–3618 | Three cards: **Pre-Flight** (affected contracts, records impacted, unknown columns, OCR/mojibake, low confidence, doc type), **Semantic** (proposals/accepted/rejected/pending), **Patch Review** (draft/submitted/at verifier/admin/RFIs/promoted). Data from `TriageAnalytics` cache. |
| **Lifecycle Progression** | `#ta-lifecycle-stages` | 3620–3627 | Horizontal stage rail: 9 lifecycle stages with counts and clickable drill-down. Rendered by `AppModules.Components.LifecycleRail`. |
| **Schema Snapshot** | 4-tile grid | 3628–3661 | Four tiles: Columns Mapped (%), Unknown Columns, Missing Values (with blank/picklist breakdown), Data Quality (accounts & addresses). Clickable for drill-down. |
| **Pre-Flight Queue** | `#p1d-preflight-container` | 3666–3678 | Sheet-tabbed issue list with type filters and live intake bar. |
| **System Pass Queue** | `#system-pass-controls` | 3681–3723 | Table of system-applied changes with re-run controls. |
| **Patch Queue** | `#patch-queue-list` | 3726–3749 | Flat table of patch requests (Type/Record/Field/Status/Updated/Actions). |
| **System Changes Queue** | `#system-queue-list` | 3751–3773 | Flat table of system-generated changes. |

**Data sources:** All sections are powered by client-side workbook analysis via `TriageAnalytics` engine. Contract/record counts come from in-memory parsed workbook data. Patch queue items come from `verifierQueueState.payloads` (hydrated from `GET /operations/queue` when DB read flag is on, otherwise localStorage).

### 1.2 What the Verifier Triage Content Provides Today

Within the same `#page-triage`, a separate `#verifier-triage-content` div (lines 3776–3834) is shown when `currentMode === 'verifier'`. It provides:

| Component | Lines | Purpose |
|-----------|-------|---------|
| Division + Status filter bar | 3782–3801 | Two dropdowns (Division, Status) + count badge |
| Patch Type tabs | 3803–3808 | All Types / Corrections / Blacklist / RFI |
| Queue tabs | 3809–3813 | Pending / Clarification / To Admin / Resolved |
| Flat queue table | 3816–3833 | Type / Record / Field / Change-Value / Comment / Submitted / Actions |

**Data source:** `verifierQueueState.payloads` — a flat array hydrated by `opsDbHydrateQueue()` from `GET /workspaces/{ws}/operations/queue?limit=200`. No batch grouping, no analyst rollup, no aging/SLA.

### 1.3 What the Standalone Org Overview Page Provides Today

A separate `#page-verifier-org` (lines 4671–4742, routed via `#/verifier-org`) was added in V2.55. It provides:

| Component | Lines | Purpose |
|-----------|-------|---------|
| KPI Summary Strip | `#vorg-summary` | 5 cards: Pending / Needs Clarification / Sent to Admin / Resolved / Total. Clickable to filter. CSS class `.vorg-kpi-strip`. |
| Filter Bar | `#vorg-filters` | Status + Type dropdowns, sticky positioned, aria-labeled. "Clear all" link. |
| Batch Queue Table | `#vorg-batch-table` | Batch Name / Source / Items / Pending / Clarify / Resolved / Age / Health. Zebra striping, count badges, health labels. |
| Drilldown Table | `#vorg-drilldown-table` | Type / Record / Field / Status / Author / Age / Actions (Approve/Reject/Resolve/Return). Loading states, amber Return styling. |

**Data source:** DB-first via `GET /workspaces/{ws}/operations/queue` (items + counts) plus `GET /workspaces/{ws}/batches` (batch metadata). Feature-flagged via `OPS_VIEW_DB_READ`/`OPS_VIEW_DB_WRITE`.

### 1.4 Overlap and Divergence Summary

| Aspect | Analyst Triage | Verifier Triage (in-frame) | Org Overview (standalone) |
|--------|---------------|---------------------------|---------------------------|
| **Container** | `#analyst-triage-content` | `#verifier-triage-content` | `#page-verifier-org` |
| **Summary metrics** | Batch Summary Strip (contracts/records/completed) | None | KPI Strip (pending/clarify/admin/resolved/total) |
| **Primary grouping** | Contract-centric (Contract Summary Table) | Flat queue (no grouping) | Batch-centric (Batch Queue Table) |
| **Lane breakdown** | 3 lane cards (Pre-Flight/Semantic/Patch) | Type tabs (Corrections/Blacklist/RFI) | Type filter dropdown |
| **Lifecycle view** | 9-stage lifecycle rail | None | None |
| **Schema view** | 4-tile schema snapshot | None | None |
| **Aging/health** | None | None | Age column + Health dot+label (Fresh/Aging/Stale) |
| **Batch drill-down** | None (contract drill-down via health filter) | None | Batch → items table |
| **Actions** | Per-item in queue tables | Approve/Reject per queue item | Approve/Reject/Resolve/Return with loading states |
| **Data source** | Client-side workbook analysis | DB queue (flat) | DB queue + batches endpoint |
| **URL state** | None (hash route `#/triage`) | None | `#/verifier-org?status=X&batch=Y&type=Z` |
| **Responsive** | Basic flex-wrap | Basic flex-wrap | KPI 2-col/1-col breakpoints, sticky filter |
| **A11y** | Minimal | Minimal | aria-labels, focus-visible, prefers-reduced-motion |

**Key divergence:** The analyst triage frame is **contract-centric** and powered by **client-side workbook analysis**. The verifier org page is **batch-centric** and powered by **DB-first endpoints**. The V2.56 unification must bridge these two models.

---

## 2. Unified IA Spec (Before / After)

### 2.1 High-Level Layout Mapping

The triage frame becomes role-adaptive. When the user is an analyst, the frame renders analyst-specific sections. When the user is a verifier or admin, the same frame slots render verifier-specific sections. No separate page is needed.

```
BEFORE (V2.55):

  Analyst → page-triage → #analyst-triage-content
  Verifier → page-triage → #verifier-triage-content (flat queue)
           → page-verifier-org → standalone dashboard (separate nav item)
  Admin → same as verifier

AFTER (V2.56):

  Analyst → page-triage → #analyst-triage-content (unchanged)
  Verifier → page-triage → #verifier-triage-content (rebuilt to mirror analyst frame structure)
           → No standalone page (deprecated, redirects to #/triage)
  Admin → same as verifier + admin-specific panels
```

### 2.2 Section-by-Section Transformation

| # | Analyst Section | Verifier Section (V2.56) | Transformation |
|---|----------------|--------------------------|----------------|
| S1 | **Batch Summary Strip** — Contracts / Records / Completed / Needs Review / Pending | **Governance Summary Strip** — Pending / Needs Clarification / Sent to Admin / Resolved / Total | Replace contract-centric counters with queue-status counters. Source: `GET /operations/queue` → `data.counts`. Clickable to filter. Merge V2.55.1 KPI strip design (tabular-nums, "items" subtitle, active fill, Total muted). |
| S2 | **Contract Summary Table** — Per-contract rows with stage/health | **Batch Summary Table** — Per-batch rows with item counts / aging / health | Replace contracts with batches. Source: `GET /batches` + client-side item grouping from queue data. Columns: Batch Name / Source / Items / Pending / Clarify / Resolved / Age / Health. Merge V2.55.1 polish (zebra, count badges, selected row). |
| S3 | **Lane Health Cards** — Pre-Flight / Semantic / Patch Review | **Work Queue Lanes** — Pending Verification / Clarification / Resolution | 3-card grid retained. Verifier lanes reflect governance workflow instead of analyst workflow. Counts sourced from DB queue items grouped by `queue_status`. Pre-Flight → "Pending Verification" (items awaiting verifier action). Semantic → "Clarification" (items in `needs_clarification` or `returned_to_analyst`). Patch Review → "Resolution" (items `sent_to_admin` or `resolved`). |
| S4 | **Lifecycle Progression** — 9 lifecycle stages | **Governance Lifecycle** — Submitted → Under Review → Clarification → Approved → Applied/Rejected | Reuse `LifecycleRail` component with verifier-specific stages derived from `PATCH_QUEUE_STATUS_MAP` buckets. 5 stages instead of 9. Source: queue items grouped by `lifecycle_status`. |
| S5 | **Schema Snapshot** — Columns Mapped / Unknown / Missing / Quality | **Governance Snapshot** — Unknown Columns / Address Merges / NA-with-Justification / Correction Coverage | Reuse 4-tile layout. Tiles redefined for governance concerns. Unknown Columns: count of unmapped headers (from schema cache if available, otherwise hidden). Address Merges: count of account merge events. NA-with-Justification: fields with NA values that have attached RFI justifications. Correction Coverage: ratio of corrections approved vs. total submitted. Source: computed from queue items + batch metadata. |
| S6 | **Pre-Flight Queue** | **Verifier Work Queue** (replaces S6–S9) | Single unified queue table replacing all 4 analyst queues. Columns: Type / Record / Field / Status / Author / Batch / Age / Actions. Batch-filterable (click batch in S2 to scope). Merge V2.55.1 drilldown table design. |
| S7 | **System Pass Queue** | *(merged into S6)* | — |
| S8 | **Patch Queue** | *(merged into S6)* | — |
| S9 | **System Changes Queue** | *(merged into S6)* | — |

### 2.3 Navigation Change

```
BEFORE:
  Sidebar: Triage → page-triage (analyst content OR verifier flat queue)
  Sidebar: Org Overview (verifier-only) → page-verifier-org

AFTER:
  Sidebar: Triage → page-triage (role-adaptive: analyst frame OR verifier frame)
  Sidebar: Org Overview → REMOVED (redirect #/verifier-org → #/triage)
  
  Hash routes:
    #/triage                          → triage page (role-adaptive)
    #/triage?batch=bat_X              → triage page with batch filter active
    #/triage?status=pending           → triage page with status filter active
    #/triage?batch=bat_X&status=Y     → combined filters
    #/verifier-org                    → 301 redirect to #/triage (backward compat)
    #/verifier-org?batch=X&status=Y   → redirect to #/triage?batch=X&status=Y
```

---

## 3. Role-Based Surface Contract

### 3.1 Section Visibility Matrix

| Section | Analyst | Verifier | Admin |
|---------|---------|----------|-------|
| S1: Summary Strip | Batch Summary (contracts/records) | Governance Summary (queue status counts) | Same as verifier |
| S2: Primary Table | Contract Summary (with health bands) | Batch Summary (with item rollups) | Same as verifier + analyst workload column |
| S3: Lane Cards | Pre-Flight / Semantic / Patch Review | Pending Verification / Clarification / Resolution | Same as verifier |
| S4: Lifecycle Rail | 9-stage analyst lifecycle | 5-stage governance lifecycle | Same as verifier |
| S5: Snapshot Tiles | Schema: Mapped / Unknown / Missing / Quality | Governance: Unknown / Merges / NA-Justified / Corrections | Same as verifier |
| S6: Work Queue | 4 separate queue tables | 1 unified queue table | Same as verifier |
| Filter bar | Sheet tabs, issue type filters | Status / Type / Batch / Author dropdowns | Same as verifier + author filter visible |
| Analyst Workload Panel | Hidden | Hidden (aggregate in S2 batch table) | Visible: per-analyst breakdown below S2 |
| Batch drill-down | Contract drill-down via health click | Click batch row → scoped queue | Same as verifier |
| Record detail | Record Inspector + Evidence Viewer | Same | Same |

### 3.2 Action Permission Matrix

| Action | Analyst | Verifier | Admin |
|--------|---------|----------|-------|
| Submit patch | ✅ Create draft → submit | ❌ | ❌ |
| Approve patch | ❌ | ✅ `status → Verifier_Approved` | ✅ `status → Admin_Approved` |
| Reject patch | ❌ | ✅ `status → Rejected` | ✅ `status → Rejected` |
| Create RFI | ✅ Create → open | ❌ | ❌ |
| Return RFI to analyst | ❌ | ✅ `custody → returned_to_analyst` | ✅ |
| Resolve RFI | ❌ | ✅ `custody → resolved` | ✅ |
| Submit correction | ✅ Create → pending_verifier | ❌ | ❌ |
| Approve correction | ❌ | ✅ `status → approved` | ✅ |
| Reject correction | ❌ | ✅ `status → rejected` | ✅ |
| Filter by author | Own items only (enforced server-side) | All authors (no filter UI) | All authors (filter UI visible) |
| View org overview | ❌ Redirects to triage | ✅ Sees governance sections | ✅ |

### 3.3 Sandbox Role Simulation Behavior

| Switch | Expected |
|--------|----------|
| Admin → Verifier (sandbox) | Triage frame shows verifier sections; data reloads with `X-Sandbox-Mode: true`, `X-Effective-Role: verifier`; author filter hidden |
| Admin → Analyst (sandbox) | Triage frame shows analyst sections; queue scoped to own items |
| Verifier → Admin (sandbox) | Not supported (verifier cannot elevate); no change |
| Analyst → Verifier (sandbox) | Not supported (analyst cannot elevate); no change |
| Any role switch while on triage | `vorgLoadData()` (or equivalent unified loader) fires; sections re-render; URL state preserved |

---

## 4. Data Contract Mapping

### 4.1 Endpoint-to-Section Mapping (DB-First)

| Section | Primary Endpoint | Params | Role Scoping | Refresh Trigger |
|---------|-----------------|--------|--------------|-----------------|
| S1: Governance Summary | `GET /workspaces/{ws}/operations/queue` | `limit=200` | `data.counts` from response | Page load, role switch, action completion |
| S2: Batch Summary | `GET /workspaces/{ws}/batches` + queue grouping | `limit=50` | All workspace batches | Page load, batch created |
| S2: Per-batch rollups | Client-side grouping of queue items by `batch_id` | — | Inherited from queue role scope | On queue refresh |
| S3: Lane cards | Client-side grouping of queue items by `queue_status` | — | Inherited from queue role scope | On queue refresh |
| S4: Governance lifecycle | Client-side grouping of queue items by `lifecycle_status` | — | Inherited from queue role scope | On queue refresh |
| S5: Governance Snapshot | Mixed: unknown columns from schema cache (if workbook loaded), corrections/RFI counts from queue data | — | Queue-scoped | On queue refresh |
| S6: Work Queue table | `GET /workspaces/{ws}/operations/queue` | `batch_id`, `queue_status`, `item_type`, `author_id` | Role-scoped per endpoint logic | On filter change, action completion |
| Actions (write) | `PATCH /patches/{id}`, `PATCH /rfis/{id}`, `PATCH /corrections/{id}` | `status`, `version` | Server-enforced custody rules | On button click |

### 4.2 No localStorage as Source of Truth

| Data | Current Source | V2.56 Source | Migration |
|------|---------------|-------------|-----------|
| Queue items | `verifierQueueState.payloads` (may be localStorage in legacy mode) | `GET /operations/queue` exclusively when `OPS_VIEW_DB_READ=true` | Feature flag `OPS_VIEW_DB_READ` must be ON. If OFF, unified triage falls back to `opsDbHydrateQueue()` which already reads from DB when flag is on. |
| Batch metadata | `GET /workspaces/{ws}/batches` | Same (already DB-first) | No change |
| Queue counts | `data.counts` from operations queue response | Same | No change |
| Filter state | URL hash params (V2.55.1) | URL hash params | No change needed |
| Schema data (S5) | Client-side workbook parse (`TriageAnalytics` cache) | Same (schema data is inherently client-side from workbook) | If no workbook is loaded, governance snapshot tiles show "—" with "Load workbook to see schema data" hint |

### 4.3 Fallback Behavior When Source Documents Are Unavailable

| Scenario | Affected Sections | Fallback |
|----------|-------------------|----------|
| No workbook loaded | S5 (Unknown Columns tile) | Show "—" with "Schema data available after workbook import" |
| No batches in workspace | S2 (Batch table) | Empty state: "No batches found. Import data to get started." |
| No queue items | S1 (all zeros), S3 (all zeros), S6 (empty table) | Show zero counts; queue table shows "No items match current filters" |
| Operations queue endpoint errors (500) | S1, S2 rollups, S3, S4, S6 | Red error banner: "Unable to load operations data. [Retry]" — same pattern as V2.55 |
| Batch endpoint errors (500) | S2 (batch names) | Batch table shows batch IDs instead of names; queue items still visible |
| Feature flag `OPS_VIEW_DB_READ` is OFF | All DB-sourced sections | Fall back to `verifierQueueState.payloads` (localStorage-hydrated); show warning badge "Limited: local data only" |

---

## 5. Batch-First Metrics Definitions

### 5.1 KPI Counters (S1: Governance Summary Strip)

| Metric | Formula | Field Source | Notes |
|--------|---------|-------------|-------|
| Pending | `data.counts.pending` | Operations queue response | Items where `queue_status = 'pending'` |
| Needs Clarification | `data.counts.needs_clarification` | Operations queue response | Items where `queue_status = 'needs_clarification'` |
| Sent to Admin | `data.counts.sent_to_admin` | Operations queue response | Items where `queue_status = 'sent_to_admin'` |
| Resolved | `data.counts.resolved` | Operations queue response | Items where `queue_status = 'resolved'` |
| Total | `data.counts.total` | Operations queue response | Sum of all queue items |

### 5.2 Batch Rollup Metrics (S2: Batch Summary Table)

| Metric | Formula | Field Source |
|--------|---------|-------------|
| Batch Name | `batch.name` | `GET /batches` response |
| Source | `batch.source` | `GET /batches` response. Badge values: `upload` / `drive` / `merge` / `import` |
| Total Items | `queueItems.filter(i => i.batch_id === bid).length` | Client-side group from queue items |
| Pending Count | `queueItems.filter(i => i.batch_id === bid && i.queue_status === 'pending').length` | Client-side group |
| Clarify Count | `queueItems.filter(i => i.batch_id === bid && i.queue_status === 'needs_clarification').length` | Client-side group |
| Resolved Count | `queueItems.filter(i => i.batch_id === bid && i.queue_status === 'resolved').length` | Client-side group |
| Age | `Math.floor((Date.now() - new Date(batch.created_at).getTime()) / 3600000)` | `batch.created_at` from batches response |
| Health Label | `age < 24h → Fresh, 24-72h → Aging, >72h → Stale` | Computed from age |

### 5.3 Per-Analyst Workload (Admin Only)

| Metric | Formula | Field Source |
|--------|---------|-------------|
| Analyst Email | `item.author_email` | Unique `author_email` values from queue items |
| Total Items | `queueItems.filter(i => i.author_id === uid).length` | Client-side group |
| Pending | `queueItems.filter(i => i.author_id === uid && i.queue_status === 'pending').length` | Client-side group |
| Open RFIs | `queueItems.filter(i => i.author_id === uid && i.item_type === 'rfi' && i.queue_status !== 'resolved').length` | Client-side group |
| Oldest Pending (hours) | `Math.max(...pendingItems.map(i => ageHours(i.created_at)))` | Computed from `created_at` |

### 5.4 Aging Buckets

| Bucket | Range (hours) | Color Token | Health Label |
|--------|--------------|-------------|--------------|
| Fresh | 0 – 24 | `var(--ok)` (#34D399 dark, #2e7d32 light) | Fresh |
| Aging | 24 – 72 | `var(--warn)` (#FBBF24 dark, #f57c00 light) | Aging |
| Stale | > 72 | `var(--bad)` (#FB7185 dark, #c62828 light) | Stale |

### 5.5 Lane Card Metrics (S3)

| Lane Card | Verifier Label | Count Formula | Sub-metrics |
|-----------|---------------|---------------|-------------|
| Lane 1 | Pending Verification | `items.filter(i => i.queue_status === 'pending').length` | By type: patches / RFIs / corrections |
| Lane 2 | Clarification | `items.filter(i => i.queue_status === 'needs_clarification').length` | Returned-to-analyst / awaiting-response |
| Lane 3 | Resolution | `items.filter(i => i.queue_status === 'sent_to_admin' || i.queue_status === 'resolved').length` | Sent to admin / resolved / applied |

### 5.6 Governance Snapshot Metrics (S5)

| Tile | Label | Formula | Source |
|------|-------|---------|--------|
| Tile 1 | Unknown Columns | `TriageAnalytics._schemaCache.unknown_count` | Client-side schema analysis (if workbook loaded) |
| Tile 2 | Address Merges | Count of `batch.metadata.address_merge_count` across active batches | `GET /batches` metadata field (or 0 if not present) |
| Tile 3 | NA-with-Justification | `queueItems.filter(i => i.item_type === 'rfi' && i.queue_status === 'resolved' && i.metadata.justification_type === 'na').length` | Queue items with resolved RFI + NA metadata |
| Tile 4 | Correction Coverage | `corrections_approved / corrections_total * 100` | Queue items of type `correction`, ratio of resolved to total |

---

## 6. UI/API Mismatch Register

### 6.1 Structural Mismatches

| ID | Issue | File / Line | Severity | Proposed Fix |
|----|-------|-------------|----------|--------------|
| UM-01 | `#verifier-triage-content` and `#page-verifier-org` are separate, disconnected containers | `index.html:3776` (in-frame), `index.html:4671` (standalone) | P0 | Rebuild `#verifier-triage-content` to include all org view sections (KPI strip, batch table, filter bar, drilldown). Remove `#page-verifier-org` page container. |
| UM-02 | `#verifier-triage-content` has no summary strip or batch table — only flat queue | `index.html:3776–3834` | P0 | Port KPI strip rendering (`vorgRenderKpi`) and batch table rendering (`vorgRenderBatchTable`) into verifier triage content. |
| UM-03 | Sidebar has separate "Org Overview" nav item with `verifier-only` class | `index.html:3139` | P1 | Remove nav item. Add redirect from `#/verifier-org` to `#/triage`. |
| UM-04 | `showPage('verifier-org')` in navigation handler creates separate page routing | `index.html:25355, 25423, 25599–25600` | P1 | Remove `verifier-org` from `pages` array. Add redirect in hash-change handler. |
| UM-05 | Two separate data loading functions: `opsDbHydrateQueue()` for verifier triage vs. `vorgLoadData()` for org page | `index.html:~39109` (hydrate), `index.html:~39340` (vorgLoad) | P1 | Unify into single `triageLoadVerifierData()` that populates both summary strip and queue table from one `/operations/queue` call. |
| UM-06 | Lane cards in analyst frame use `TriageAnalytics` cache (client-side), but verifier needs DB-sourced queue counts | `index.html:3576–3618` (analyst lanes), `operations_queue.py` (DB data) | P1 | Verifier lane cards compute from queue items array rather than `TriageAnalytics` cache. Analyst lanes remain unchanged. |
| UM-07 | Schema Snapshot tiles reference analyst-specific `TriageAnalytics._schemaCache` which is not populated in verifier mode | `index.html:3628–3661` | P2 | Governance Snapshot tiles conditionally show schema data only if workbook is loaded. Otherwise show "—" with explanation. |
| UM-08 | Lifecycle rail (`LifecycleRail.render`) uses analyst lifecycle stages from `TriageAnalytics` cache | `index.html:18062–18093` | P2 | Create verifier-specific lifecycle stage definition (5 governance stages). Conditionally render based on role. |
| UM-09 | Filter bar in verifier triage uses Division/Status dropdowns with no URL state sync | `index.html:3782–3801` | P1 | Replace with unified filter bar (Status/Type/Batch/Author) with URL hash sync, matching V2.55.1 pattern. |
| UM-10 | `verifierQueueState` is a flat array with no batch grouping capability | `index.html:~39093` | P1 | Replace with `_vorgState` structure which already supports `batchMap`, `queueItems`, `activeBatchId`, `activeKpiStatus`. |

### 6.2 CSS/Visual Mismatches

| ID | Issue | File / Line | Severity | Proposed Fix |
|----|-------|-------------|----------|--------------|
| UM-11 | V2.55.1 CSS classes (`.vorg-kpi-strip`, `.vorg-filter-bar`, `.vorg-kpi`, etc.) are scoped to `#page-verifier-org` visually but will need to work inside `#verifier-triage-content` | `index.html:376–441` (CSS block) | P1 | CSS selectors are class-based (not ID-scoped), so they will work in any container. Verify no ID-based selectors conflict. |
| UM-12 | `#verifier-triage-content` has its own filter bar styles (`.verifier-filter-bar`) that conflict with `.vorg-filter-bar` | `index.html:3782` | P2 | Remove legacy `.verifier-filter-bar` once unified filter replaces it. |
| UM-13 | Dark mode rules for org page use `#vorg-*` selectors that won't apply if containers change | `index.html:425–441` | P2 | All dark mode rules already use class selectors (`.vorg-kpi`, `.vorg-filter-bar`, etc.) — no change needed. Verified. |

### 6.3 Backend Mismatches

| ID | Issue | File / Line | Severity | Proposed Fix |
|----|-------|-------------|----------|--------------|
| UM-14 | Operations queue does double-query for counts (queries all items twice: once for list, once for counts ignoring `author_id`) | `operations_queue.py:220–232` | P3 (performance) | No fix needed for V2.56 — acceptable at current scale. Optimize in V2.57 with `COUNT(*) GROUP BY queue_status` subquery. |
| UM-15 | `GET /batches` returns no item rollup counts — requires client-side join with queue data | `batches.py:39–89` | P2 | No backend change in V2.56. Client-side grouping is acceptable. Consider `GET /batches/rollups` endpoint in V2.57. |
| UM-16 | No `batch_name` field on queue items — client must maintain `batch_id → name` lookup | `operations_queue.py:56–81` | P3 | No fix in V2.56. Client-side map from batches list is sufficient. |

---

## 7. Acceptance Criteria

| # | Criterion | Test Method | Pass Condition |
|---|-----------|-------------|----------------|
| AC-01 | Verifier sees governance summary strip in triage page | Navigate to `#/triage` as verifier | KPI cards show Pending / Clarify / Sent to Admin / Resolved / Total with correct counts |
| AC-02 | Verifier sees batch summary table in triage page | Navigate to `#/triage` as verifier | Batch table renders with Name / Source / Items / Pending / Clarify / Resolved / Age / Health |
| AC-03 | Verifier sees lane cards with governance labels | Navigate to `#/triage` as verifier | Three cards: "Pending Verification" / "Clarification" / "Resolution" with correct counts |
| AC-04 | Verifier sees governance lifecycle rail | Navigate to `#/triage` as verifier | 5-stage rail: Submitted → Under Review → Clarification → Approved → Applied/Rejected |
| AC-05 | Verifier sees governance snapshot tiles | Navigate to `#/triage` as verifier | 4 tiles render; if no workbook, "Unknown Columns" shows "—" with hint |
| AC-06 | Verifier sees unified work queue | Scroll down on triage page | Single queue table with Type / Record / Field / Status / Author / Batch / Age / Actions |
| AC-07 | Analyst sees unchanged triage | Navigate to `#/triage` as analyst | All existing analyst sections render identically to V2.55.1 |
| AC-08 | `#/verifier-org` redirects to `#/triage` | Navigate to `#/verifier-org` as verifier | URL changes to `#/triage`; triage page renders |
| AC-09 | `#/verifier-org?batch=X&status=Y` preserves params on redirect | Navigate with params | URL becomes `#/triage?batch=X&status=Y`; filters applied |
| AC-10 | Org Overview sidebar item removed for verifier | Check sidebar in verifier mode | No "Org Overview" nav item; "Triage" is the only entry point |
| AC-11 | KPI click → filters queue and batch table | Click "Pending" KPI | Queue filters to pending items; batch table highlights matching counts; URL updates |
| AC-12 | Batch row click → scoped queue | Click batch row | Queue table filters to that batch; "Back to all" link visible |
| AC-13 | Admin sees analyst workload panel | Switch to admin in sandbox | Per-analyst breakdown table visible below batch summary |
| AC-14 | Verifier does NOT see analyst workload panel | Switch to verifier | No analyst breakdown visible |
| AC-15 | Action buttons work in unified queue | Approve a patch in queue table | Toast confirms; item status updates; version bumps; counts refresh |
| AC-16 | Sandbox role switch refreshes triage correctly | Switch verifier → admin → analyst in sandbox | Each switch: triage content re-renders for correct role; data reloads |
| AC-17 | Dark mode renders all unified sections correctly | Toggle dark mode as verifier | All sections use theme tokens; no white flashes; contrast passes WCAG AA |
| AC-18 | Responsive: 768px viewport | Resize to 768px | KPI wraps to 2-col; batch table scrolls; filter bar wraps |
| AC-19 | Responsive: 480px viewport | Resize to 480px | KPI stacks single-col; tables scrollable; actions accessible |
| AC-20 | URL state sync for filters | Apply status + batch filter; refresh page | Filters restored from URL hash |
| AC-21 | Empty workspace renders correctly | Clear all data | Zero counts; "No batches found" message; "No items" in queue |
| AC-22 | Error state renders correctly | Simulate 500 from operations queue | Red error banner with "Retry" button |
| AC-23 | Feature flag OFF fallback | Set `OPS_VIEW_DB_READ=false` | Warning badge shows; data loads from local state |
| AC-24 | Production parity with sandbox | Compare real verifier account vs. sandbox-simulated verifier | Same sections, same data scope, same action availability |

---

## 8. QA Plan

### 8.1 Role Matrix Tests

| # | Scenario | Setup | Steps | Expected |
|---|----------|-------|-------|----------|
| QA-01 | Analyst triage unchanged | Log in as analyst | Navigate to `#/triage` | Analyst triage content renders: batch summary, contract table, lane cards, lifecycle rail, schema snapshot, 4 queue sections. No governance sections visible. |
| QA-02 | Verifier triage shows governance | Log in as verifier | Navigate to `#/triage` | Governance summary strip, batch table, lane cards, lifecycle rail, governance snapshot, unified queue. No analyst sections visible. |
| QA-03 | Admin triage shows governance + workload | Log in as admin | Navigate to `#/triage` | Same as verifier + analyst workload panel visible below batch table. |
| QA-04 | Sandbox analyst → verifier | Log in as admin, switch to analyst, then verifier | Toggle role in sandbox | Triage re-renders: analyst content hidden, verifier content shown. Data reloads with `X-Effective-Role: verifier`. |
| QA-05 | Sandbox verifier → admin | Log in as admin, switch to verifier, then back to admin | Toggle role | Analyst workload panel appears; data reloads. |
| QA-06 | Sandbox admin → analyst | Switch to analyst | Toggle role | Governance sections hidden; analyst sections shown. Org-level data not visible. |

### 8.2 Multi-Analyst Concurrency Tests

| # | Scenario | Setup | Steps | Expected |
|---|----------|-------|-------|----------|
| QA-07 | Two verifiers approve same patch | Open two browser sessions as different verifiers | Both click Approve on same patch simultaneously | First succeeds (200, version bumps); second gets 409 toast "Version conflict — refresh to retry". |
| QA-08 | Analyst submits while verifier is viewing | Analyst submits new patch while verifier has triage open | Verifier refreshes | New patch appears in queue; pending count increments. |
| QA-09 | Verifier approves, admin sees update | Verifier approves patch; admin refreshes triage | Admin clicks refresh | Item moves from "pending" to "sent_to_admin"; counts update. |

### 8.3 Cross-Workspace Isolation Tests

| # | Scenario | Setup | Steps | Expected |
|---|----------|-------|-------|----------|
| QA-10 | Verifier in workspace A sees no workspace B data | Create items in workspace B | Verifier navigates to triage in workspace A | Zero items from workspace B appear. Batch table shows only workspace A batches. |
| QA-11 | Analyst in workspace A cannot see verifier sections | Analyst role in workspace A only | Navigate to `#/triage` | Only analyst content visible. No governance KPI strip or batch table. |

### 8.4 Batch Ingest Split Tests

| # | Scenario | Setup | Steps | Expected |
|---|----------|-------|-------|----------|
| QA-12 | Upload batch appears in batch table | Upload XLSX via analyst triage | Switch to verifier, view triage | New batch appears in batch table with source="upload". |
| QA-13 | Drive batch appears with dedupe | Import from Google Drive | View triage as verifier | Batch appears with source="drive". Re-importing same revision returns existing batch (200), no duplicate row. |
| QA-14 | Mixed batches with per-batch rollups | Create 3 batches (upload, drive, merge) with varying item counts | View triage as verifier | All 3 batches in table; counts per batch correct; total in KPI strip matches sum. |

### 8.5 Regression Tests

| # | Check | Method | Expected |
|---|-------|--------|----------|
| QA-15 | Patch approve/reject flow | Approve + reject patches from unified queue | Toast confirms; status transitions correct per lifecycle rules. |
| QA-16 | RFI resolve/return flow | Resolve + return RFIs | Correct custody transitions; return uses `returned_to_analyst`. |
| QA-17 | Correction approve/reject flow | Approve + reject corrections | Status transitions correct. |
| QA-18 | URL state persistence | Apply filters, refresh page | Filters restored from URL hash params. |
| QA-19 | `#/verifier-org` backward compat | Navigate to old URL | Redirects to `#/triage` with params preserved. |
| QA-20 | Empty/loading/error states | Test all three | Loading spinner, empty message, error banner all render correctly. |
| QA-21 | Dark mode full pass | Toggle dark mode, exercise all verifier sections | No contrast failures, no white flashes, all tokens correct. |

---

## 9. Clarity Questions (Blocking Only)

| # | Question | Impact | Recommendation |
|---|----------|--------|----------------|
| CQ-01 | Should the unified triage for verifier/admin retain the legacy `#verifier-triage-content` flat queue (Division/Status/Type tabs) as a secondary view mode, or fully replace it? | If retained, two verifier queue views coexist. If replaced, simpler but any users relying on Division filter lose it. | **Recommend full replacement.** The unified batch-first queue is strictly superior. Division filter can be added as a dropdown in the unified filter bar if needed. No users have reported dependency on the legacy flat queue. |
| CQ-02 | Should governance lifecycle rail reuse the existing `LifecycleRail` component with different stage definitions, or create a new component? | Reuse reduces code duplication but requires the component to accept dynamic stage configs. | **Recommend reuse.** Modify `LifecycleRail.render(cache)` to accept an optional `stages` array parameter. When provided, override the default 9-stage analyst lifecycle with the 5-stage governance lifecycle. Single component, two configurations. |
| CQ-03 | When no workbook is loaded, should the verifier governance snapshot tiles (S5) be hidden entirely, or shown with placeholder values? | Hiding makes the frame shorter but breaks visual consistency. Placeholders maintain layout. | **Recommend placeholders.** Show "—" values with "Load workbook for schema data" subtitle on tiles that depend on schema analysis (Tile 1: Unknown Columns). Tiles that use DB data (Tile 3: NA-Justified, Tile 4: Corrections) should always compute from queue items regardless of workbook state. |
| CQ-04 | Should the `#/verifier-org` route redirect (backward compat) be a permanent redirect, or should the org page remain accessible as an alias for a defined deprecation period? | If permanent redirect, clean break. If alias, old bookmarks still work but two code paths remain temporarily. | **Recommend immediate redirect.** V2.55 org page has been live for <1 day; no external bookmarks exist. Clean redirect avoids maintaining two rendering paths. Console log: `[V2.56] #/verifier-org deprecated — redirecting to #/triage`. |
| CQ-05 | Should the analyst workload panel (admin-only, S2 extension) show per-analyst email addresses or anonymized IDs in non-production environments? | Privacy concern for sandbox/demo modes. | **Recommend full emails.** The admin role already has access to user emails via the People & Access tab. Sandbox mode uses `sandbox_user` which has no real PII. No additional exposure. |

---

## 10. Go/No-Go + Phased Task List

### Verdict: GO (with phased execution)

All changes are within the existing `ui/viewer/index.html` frontend. No new backend endpoints required. No database migrations. The operations queue endpoint and batches endpoint already provide all needed data. CSS from V2.55.1 transfers directly into the unified frame.

### Phased Task List

| Task ID | Description | Priority | Scope | Dependencies | Estimate |
|---------|-------------|----------|-------|-------------|----------|
| VTRIAGE-01 | **Rebuild `#verifier-triage-content` container** — Remove legacy Division/Status/Type tabs and flat queue. Create placeholder divs for S1–S6 sections matching analyst frame structure. | P0 | HTML structure | None | 1 session |
| VTRIAGE-02 | **Unify data loader** — Merge `opsDbHydrateQueue()` and `vorgLoadData()` into single `triageLoadVerifierData()` that fetches operations queue + batches, builds batch rollup map, and populates all section containers. | P0 | JS | VTRIAGE-01 | 1 session |
| VTRIAGE-03 | **Port KPI strip + batch table renderers** — Move `vorgRenderKpi()`, `vorgRenderBatchTable()`, and associated CSS from org page scope into verifier triage content. Reuse existing `.vorg-*` CSS classes. | P0 | JS + CSS | VTRIAGE-01, VTRIAGE-02 | 1 session |
| VTRIAGE-04 | **Port unified filter bar + URL sync** — Replace legacy Division/Status filter bar with unified Status/Type/Batch filter bar using `.vorg-filter-bar` pattern. Wire URL hash sync (`#/triage?status=X&batch=Y`). | P1 | JS + HTML | VTRIAGE-01, VTRIAGE-03 | 1 session |
| VTRIAGE-05 | **Build verifier lane cards (S3)** — Create 3-card grid: Pending Verification / Clarification / Resolution. Compute counts from queue items. Reuse `.ta-lane-card` styling with verifier-specific labels and colors. | P1 | JS + HTML | VTRIAGE-02 | 1 session |
| VTRIAGE-06 | **Build governance lifecycle rail (S4)** — Extend `LifecycleRail.render()` to accept verifier-specific 5-stage definition. Conditionally render based on `currentMode`. | P2 | JS | VTRIAGE-02 | 0.5 session |
| VTRIAGE-07 | **Build governance snapshot tiles (S5)** — Create 4-tile grid: Unknown Columns / Address Merges / NA-with-Justification / Correction Coverage. Conditionally show schema data. Compute correction/RFI metrics from queue items. | P2 | JS + HTML | VTRIAGE-02 | 1 session |
| VTRIAGE-08 | **Port unified work queue table (S6)** — Move drilldown table rendering from org page into triage content as the primary queue view. Add Batch column. Wire action buttons. | P1 | JS + HTML | VTRIAGE-02, VTRIAGE-03 | 1 session |
| VTRIAGE-09 | **Add admin analyst workload panel** — Render per-analyst breakdown table below batch summary when `currentMode === 'admin'`. Columns: Email / Total / Pending / Open RFIs / Oldest Pending. Compute from queue items grouped by `author_id`. | P2 | JS + HTML | VTRIAGE-02 | 0.5 session |
| VTRIAGE-10 | **Deprecate standalone org page** — Remove `#page-verifier-org` container from HTML. Remove `verifier-org` from sidebar nav. Add redirect in hash-change handler: `#/verifier-org` → `#/triage`. Remove `vorgLoadData()` function (replaced by VTRIAGE-02). | P1 | HTML + JS | VTRIAGE-01–VTRIAGE-09 | 0.5 session |
| VTRIAGE-11 | **Role-switch integration** — Wire sandbox role-switch handler to call unified `triageLoadVerifierData()`. Ensure `showPage('triage')` toggles between analyst and verifier content containers based on `currentMode`. | P1 | JS | VTRIAGE-02, VTRIAGE-10 | 0.5 session |
| VTRIAGE-12 | **Dark mode validation pass** — Verify all ported sections render correctly in dark mode. Ensure `.vorg-*` dark mode rules apply inside verifier triage content. Test against Palette B tokens. | P2 | CSS | VTRIAGE-01–VTRIAGE-11 | 0.5 session |
| VTRIAGE-13 | **Responsive validation pass** — Test unified triage at 768px and 480px breakpoints. Verify KPI wrap, table scroll, filter bar stack. Fix any layout regressions. | P2 | CSS | VTRIAGE-01–VTRIAGE-11 | 0.5 session |
| VTRIAGE-14 | **A11y validation pass** — Verify focus-visible outlines, aria-labels, role attributes, prefers-reduced-motion on all new/ported elements. Run keyboard-only navigation test. | P3 | HTML + CSS | VTRIAGE-01–VTRIAGE-13 | 0.5 session |

### Dependency Graph

```
VTRIAGE-01 (container rebuild)
  ├── VTRIAGE-02 (data loader)
  │     ├── VTRIAGE-03 (KPI + batch table)
  │     │     └── VTRIAGE-04 (filter bar + URL sync)
  │     ├── VTRIAGE-05 (lane cards)
  │     ├── VTRIAGE-06 (lifecycle rail)
  │     ├── VTRIAGE-07 (governance snapshot)
  │     ├── VTRIAGE-08 (work queue table)
  │     └── VTRIAGE-09 (admin workload panel)
  └── VTRIAGE-10 (deprecate org page) ← depends on all above
        └── VTRIAGE-11 (role-switch integration)
              ├── VTRIAGE-12 (dark mode)
              ├── VTRIAGE-13 (responsive)
              └── VTRIAGE-14 (a11y)
```

### Estimated Total: ~9 sessions

### Constraints Recap
- No backend code changes in V2.56
- No new API endpoints
- No database migrations
- All changes within `ui/viewer/index.html` (HTML + CSS + JS)
- Backward-compatible: `#/verifier-org` redirects to `#/triage`
- Feature flags `OPS_VIEW_DB_READ` / `OPS_VIEW_DB_WRITE` behavior unchanged
- Dark mode via existing `theme.css` tokens
- Analyst triage completely unaffected
