# V2.55 — Verifier Organizational View: Clarity Document

**Status:** Draft — DOC + CLARITY ONLY  
**Date:** 2026-02-17  
**Scope:** Design specification for verifier-facing organizational dashboard  
**Depends on:** V2.54.1 (role-scoped queue, custody transitions, drive batch dedupe — all complete)

---

## 1. Audit Snapshot (Current UI Behavior)

### 1.1 What Verifier Currently Sees

| Panel | File/Line | Current Behavior | Gap |
|-------|-----------|------------------|-----|
| Mode switcher | `ui/viewer/index.html:3147` | Button toggles to "Verifier" mode, sets `currentMode = 'verifier'` | Switches chrome only — no org-level dashboard view |
| Verifier triage panel | `ui/viewer/index.html:3703-3793` | `#verifier-triage-content` with filter bar (division, status), tabbed queue (pending/approved/flagged), table listing queue items | Flat list of items — no batch grouping, no analyst rollup, no aging/SLA |
| Verifier filter bar | `ui/viewer/index.html:3709-3727` | Two dropdowns: `#verifier-filter-division` + `#verifier-filter-status`, count badge | No age filter, no batch filter, no analyst filter |
| Verifier queue table | `ui/viewer/index.html:3743-3756` | Table with columns: Record, Field, Status, Division, Analyst, Actions | Per-item view — no aggregate counts or KPIs |
| Verifier Review page | `ui/viewer/index.html:4598-4824` | `#page-verifier-review` — deep review of single patch with evidence/checklist, approve/reject buttons | Good for single-item review, but no way to navigate from org overview |
| `verifierQueueState` | `ui/viewer/index.html:39093` | `{ payloads: [], activeQueue: 'pending' }` — flat array of all queue items | No batch-level grouping, no analyst aggregation, no age bucketing |
| `opsDbHydrateQueue()` | `ui/viewer/index.html:39109-39158` | Fetches from `GET /operations/queue?limit=200`, merges into `verifierQueueState.payloads` | Single flat fetch — no rollup data, no batch-scoped queries |
| `updatePayloadStatus()` | `ui/viewer/index.html:43316-43395` | Dispatches to `opsDbWriteStatus` / `opsDbWriteRfiStatus` / `opsDbWriteCorrectionStatus` by type | Per-item actions only — no bulk triage |
| `vrApprove()` / `vrReject()` | `ui/viewer/index.html:44533/44564` | Single-patch approve/reject with DB write | No batch-level approve |
| Role simulation | `ui/viewer/index.html:25804` | `opsOnRoleSwitch()` clears queue and re-hydrates on role change | Works correctly post-P0 fix |
| Grid filter bar (verifier) | `ui/viewer/index.html:3775-3793` | `#verifier-grid-filter-bar` — secondary filter for grid view in verifier mode | Separate from triage, not connected to org overview |

### 1.2 Summary of Gaps vs. Desired Org-Level Oversight

| Gap | Impact |
|-----|--------|
| No org summary strip (KPI dashboard) | Verifier has no at-a-glance view of workspace health |
| No batch queue table | Cannot see which batches need attention, batch-level progress |
| No analyst workload panel | Cannot see workload distribution or identify bottlenecks |
| No SLA/aging panel | No visibility into aging items or SLA breaches |
| No risk/blocked panel | Blockers (open RFIs, pending corrections, mojibake docs) not surfaced |
| No drill-down side panel | Must navigate away from queue to inspect items |
| No bulk triage | Must approve/reject/clarify one item at a time |
| No URL state / deep-link filters | Filters not preserved in URL, cannot share filtered views |

---

## 2. Information Architecture — Verifier Org View

### 2.1 Layout Zones

```
┌──────────────────────────────────────────────────────────────────┐
│ [1] Org Summary Strip                                            │
│  ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐ ┌────────┐        │
│  │Pending │ │At Ver. │ │Clarify │ │Resolved│ │Blocked │        │
│  │   42   │ │   18   │ │    7   │ │  156   │ │    3   │        │
│  └────────┘ └────────┘ └────────┘ └────────┘ └────────┘        │
├──────────────────────────────────────────────────────────────────┤
│ [2] Batch Queue Table                  │ [5] Drill-Down Panel    │
│  Batch          | Items | Age | Health │                         │
│  bat_ABC upload |  24   | 2d  | ⚠️     │  Record: rec_123        │
│  bat_DEF drive  |  12   | 4h  | ✅     │  Field: artist_name     │
│  bat_GHI upload |   8   | 3d  | 🔴     │  Evidence: [inline]     │
│─────────────────────────────────────── │  Actions: [Approve]     │
│ [3] Analyst Workload Panel             │           [Reject]      │
│  analyst@a.com  | 14 items | 2 RFIs   │           [Clarify]     │
│  analyst@b.com  |  8 items | 0 RFIs   │                         │
│─────────────────────────────────────── │                         │
│ [4] SLA / Aging Panel                  │                         │
│  0-24h: 12  │ 24-72h: 18 │ 72h+: 5   │                         │
│  ⚠️ 3 items > SLA threshold            │                         │
│─────────────────────────────────────── │                         │
│ [6] Risk / Blocked Panel               │                         │
│  🔴 2 batches with mojibake docs       │                         │
│  ⚠️ 5 RFIs awaiting analyst response   │                         │
│  ⚠️ 3 corrections pending verifier     │                         │
└──────────────────────────────────────────────────────────────────┘
```

### 2.2 Zone Specifications

| Zone | ID | Purpose | Visibility |
|------|----|---------|------------|
| Org Summary Strip | `#vorg-summary` | KPI counters — clickable to filter queue | Verifier + Admin |
| Batch Queue Table | `#vorg-batches` | Sortable table of active batches with rollup counts | Verifier + Admin |
| Analyst Workload Panel | `#vorg-analysts` | Per-analyst item counts, open RFI counts | Admin only (verifier sees aggregate) |
| SLA / Aging Panel | `#vorg-aging` | Age-bucketed item counts with SLA indicators | Verifier + Admin |
| Drill-Down Side Panel | `#vorg-drilldown` | Context pane for selected batch/record/evidence | Verifier + Admin |
| Risk / Blocked Panel | `#vorg-blockers` | Blocker indicators from batch health data | Verifier + Admin |

### 2.3 Navigation Hierarchy

```
Workspace View (org summary)
  └── Batch Detail (filtered queue for one batch)
        └── Record Detail (record inspector with field list)
              └── Evidence / Annotation Actions
                    ├── Approve patch
                    ├── Reject patch
                    ├── Send RFI to analyst
                    ├── Approve correction
                    └── View evidence pack / source doc
```

### 2.4 URL State Strategy

All filter state persists in URL hash for deep-linking and shareability:

```
#/verifier-org                                          → Org overview (default)
#/verifier-org?batch=bat_ABC                            → Batch drill-down
#/verifier-org?batch=bat_ABC&analyst=usr_123             → Batch + analyst filter
#/verifier-org?batch=bat_ABC&age=72h_plus               → Batch + age filter
#/verifier-org?status=needs_clarification               → Cross-batch status filter
#/verifier-org?batch=bat_ABC&record=rec_456             → Record detail in side panel
```

**Persistent filters:** Status, batch, analyst, age bucket, item type (patch/rfi/correction).  
**Filter state sync:** URL ↔ `vorgFilterState` object ↔ UI dropdowns. Any change updates all three.

---

## 3. Data Contract for UI Modules

### 3.1 Module Data Sources

| Module | Primary Endpoint | Query Params | Role Scope | Refresh |
|--------|-----------------|--------------|------------|---------|
| Org Summary Strip | `GET /workspaces/{ws}/operations/queue` | `limit=200` (counts only) | Verifier: workspace-wide | Manual + on role switch |
| Batch Queue Table | `GET /workspaces/{ws}/batches` | `limit=50` | Workspace-wide (all roles) | Manual |
| Batch Health | `GET /batches/{id}/health` (per batch) | — | Workspace member | On batch select |
| Analyst Workload | `GET /workspaces/{ws}/operations/queue` | `author_id={usr}` per analyst | Admin: all analysts; Verifier: aggregate | Manual |
| SLA / Aging | Computed client-side from queue `created_at` fields | — | Same as queue | On queue refresh |
| Drill-Down (patches) | `GET /workspaces/{ws}/patches` | `batch_id=X` | Role-scoped (P3) | On batch select |
| Drill-Down (RFIs) | `GET /workspaces/{ws}/rfis` | `batch_id=X` | Role-scoped (P3) | On batch select |
| Drill-Down (corrections) | `GET /workspaces/{ws}/corrections` | `batch_id=X` | Role-scoped (P3) | On batch select |
| Record Detail | `GET /patches/{id}`, `GET /rfis/{id}` | — | Workspace member | On record select |
| Evidence Pack | `GET /patches/{pat_id}/evidence-packs` | — | Workspace member | On record select |
| Audit Trail | `GET /workspaces/{ws}/audit-events` | `resource_id=X` | Workspace member | On record select |

### 3.2 Normalized Client Models

#### 3.2.1 Batch Rollup Model

```javascript
{
  batch_id: "bat_ABC",
  name: "Q4 Upload",
  source: "upload" | "drive" | "merge" | "import",
  created_at: "2026-02-15T10:00:00Z",
  status: "active" | "closed",
  counts: {
    patches_pending: 12,
    patches_approved: 8,
    patches_rejected: 2,
    rfis_open: 3,
    rfis_awaiting_verifier: 1,
    corrections_pending: 2,
    total_items: 28,
    total_actionable: 18
  },
  health: {
    rfis_open: 3,
    rfis_awaiting_verifier: 1,
    corrections_pending: 2,
    mojibake_suspect_docs: 0,
    reader_unreadable_docs: 0,
    blockers: []
  },
  age_hours: 48,
  gate_color: "green" | "amber" | "red"
}
```

#### 3.2.2 Analyst Rollup Model

```javascript
{
  analyst_id: "usr_123",
  email: "analyst@example.com",
  counts: {
    patches_total: 14,
    patches_pending: 6,
    rfis_open: 2,
    rfis_awaiting_verifier: 1,
    corrections_pending: 1
  },
  oldest_pending_hours: 72,
  sla_status: "ok" | "warning" | "breached"
}
```

#### 3.2.3 Queue Card Model (patch / rfi / correction)

```javascript
{
  id: "pat_ABC" | "rfi_DEF" | "cor_GHI",
  type: "patch" | "rfi" | "correction",
  batch_id: "bat_XYZ",
  record_id: "rec_123",
  field_key: "artist_name",
  queue_status: "pending" | "needs_clarification" | "sent_to_admin" | "resolved",
  status: "Submitted" | "open" | "pending_verifier",
  custody_status: null | "open" | "awaiting_verifier" | "returned_to_analyst" | "resolved",
  author_id: "usr_123",
  author_email: "analyst@example.com",
  created_at: "2026-02-15T10:00:00Z",
  version: 3,
  age_hours: 48,
  age_bucket: "0-24h" | "24-72h" | "72h+"
}
```

#### 3.2.4 Aging Buckets

| Bucket | Range | Color | Label |
|--------|-------|-------|-------|
| Fresh | 0–24h | `--ok` (#34D399) | On track |
| Aging | 24–72h | `--warn` (#FBBF24) | Needs attention |
| Stale | 72h+ | `--bad` (#FB7185) | Overdue |

---

## 4. Verifier UX Behavior Specs

### 4.1 Queue Interactions

| Action | Trigger | Backend | UI Response |
|--------|---------|---------|-------------|
| Approve patch | Click "Approve" on queue row or drill-down | `PATCH /patches/{id}` with `status: "Verifier_Approved"` | Row moves to "resolved" tab, version bumps, toast confirmation |
| Reject patch | Click "Reject" | `PATCH /patches/{id}` with `status: "Rejected"` | Row moves to "resolved" tab, version bumps, toast confirmation |
| Request clarification (RFI) | Click "Clarify" on queue row | `PATCH /rfis/{id}` with `custody_status: "returned_to_analyst"` | Row moves to "needs_clarification" tab |
| Resolve RFI | Click "Resolve" on RFI in queue | `PATCH /rfis/{id}` with `custody_status: "resolved"` | Row moves to "resolved" tab |
| Approve correction | Click "Approve" on correction row | `PATCH /corrections/{id}` with `status: "approved"` | Row moves to "resolved" tab |

#### Bulk Triage Affordances

| Affordance | Behavior |
|------------|----------|
| Select-all checkbox | Selects visible queue items (filtered) |
| Bulk approve | Sends sequential PATCH requests for each selected patch; progress bar shows completion |
| Bulk reject | Same as bulk approve with reject status |
| Conflict handling | If any item returns 409 STALE_VERSION: skip that item, continue others, show summary toast listing skipped items with "refresh to retry" link |
| Error handling | If any item returns 500: stop batch, show error toast, list completed vs. remaining |

### 4.2 Drill-Down Behavior

| Trigger | Result |
|---------|--------|
| Click KPI counter in org summary | Filter batch queue table to matching status |
| Click batch row in batch table | Open batch drill-down: show all items for that batch, populate drill-down panel header with batch metadata |
| Click queue item row | Open record detail in side panel: show record inspector, evidence, annotations |
| Click evidence link in drill-down | Open Evidence Viewer in context pane (same viewer as analyst mode) |
| Click analyst name in workload panel | Filter queue to that analyst's items only |
| Click age bucket count | Filter queue to items in that age range |

### 4.3 Empty / Loading / Error States

| State | Presentation |
|-------|-------------|
| Loading (queue fetch) | Skeleton loader in each panel zone; KPI counters show "—" |
| Empty workspace (no items) | Org summary shows all zeros; batch table shows "No batches with active items" with CTA to import |
| Empty filtered view | Table body shows "No items match filters" with "Clear filters" link |
| Error (500 on queue) | Red banner at top of org view: "Unable to load queue. Retry?" with retry button |
| Error (409 on action) | Inline toast: "This item was modified by another user. Refresh to see latest." |
| Error (403 on action) | Inline toast: "You don't have permission to perform this action." |
| Stale version on bulk | Summary toast: "Approved 8/10 items. 2 skipped due to version conflict. Refresh to retry." |

### 4.4 Permission-Aware UI States

| Element | Analyst | Verifier | Admin |
|---------|---------|----------|-------|
| Org summary strip | Hidden | Visible | Visible |
| Batch queue table | Hidden | Visible | Visible |
| Analyst workload panel | Hidden | Aggregate counts only | Full per-analyst breakdown |
| Approve/Reject buttons | Hidden | Visible | Visible |
| Bulk triage | Hidden | Visible | Visible |
| Individual analyst filter | Hidden | Hidden | Visible (can filter by analyst) |
| Role simulation badge | N/A | N/A | Visible in sandbox mode |

---

## 5. Metrics & Panels Spec

### 5.1 KPI Definitions

| KPI | Source | Computation | Display |
|-----|--------|-------------|---------|
| Pending | Operations queue | Count where `queue_status = 'pending'` | Counter badge, clickable |
| At Verifier | Operations queue | Count where `queue_status = 'sent_to_admin'` or `custody_status = 'awaiting_verifier'` | Counter badge |
| Needs Clarification | Operations queue | Count where `queue_status = 'needs_clarification'` or `custody_status = 'returned_to_analyst'` | Counter badge |
| Resolved | Operations queue | Count where `queue_status = 'resolved'` | Counter badge |
| Blocked | Batch health (aggregated) | Sum of `blockers.length > 0` across all active batches | Counter badge, red if > 0 |

### 5.2 By-Batch Breakdown

| Column | Source | Notes |
|--------|--------|-------|
| Batch Name | `GET /batches` → `name` | Sortable |
| Source | `GET /batches` → `source` | Badge: upload/drive/merge/import |
| Total Items | Operations queue filtered by `batch_id` | Sum of patches + RFIs + corrections |
| Actionable | Operations queue | Non-resolved items |
| Open RFIs | `GET /batches/{id}/health` → `rfis_open` | Amber if > 0 |
| Pending Corrections | `GET /batches/{id}/health` → `corrections_pending` | Amber if > 0 |
| Age | `GET /batches` → `created_at` | Relative time, color-coded |
| Health Gate | Computed from health counts | Green / Amber / Red |

### 5.3 By-Analyst Breakdown (Admin Only)

| Column | Source | Notes |
|--------|--------|-------|
| Analyst Email | Operations queue → `author_email` | Unique analyst IDs from queue |
| Total Items | Count of items where `author_id = analyst` | — |
| Pending | Count where pending + author match | — |
| Open RFIs | Count of RFIs with open/awaiting status by author | — |
| Oldest Pending | `MAX(age_hours)` for pending items by analyst | Red if > 72h |

### 5.4 By-Age Breakdown

| Bucket | Range | Color Token | Badge Rule |
|--------|-------|-------------|------------|
| Fresh | 0–24h | `--ok` / `#34D399` | Default (no badge) |
| Aging | 24–72h | `--warn` / `#FBBF24` | Amber dot on items and batch row |
| Stale | 72h+ | `--bad` / `#FB7185` | Red dot, SLA alert indicator |

### 5.5 Blocker Indicators

| Indicator | Source | Trigger | Display |
|-----------|--------|---------|---------|
| RFI awaiting analyst | Queue: `custody_status = 'returned_to_analyst'` | count > 0 | Amber badge with count |
| Correction pending verifier | Batch health: `corrections_pending` | count > 0 | Amber badge |
| Mojibake suspect docs | Batch health: `mojibake_suspect_docs` | count > 0 | Red badge |
| Reader unreadable docs | Batch health: `reader_unreadable_docs` | count > 0 | Red badge |
| Role mismatch | Not applicable at verifier level | — | — |

### 5.6 Color/Status Semantics

| Status | Light Mode | Dark Mode Token | Badge Style |
|--------|-----------|-----------------|-------------|
| Pending | `#fff3e0` bg / `#e65100` text | `--warn` | Filled amber chip |
| Approved | `#e8f5e9` bg / `#2e7d32` text | `--ok` | Filled green chip |
| Rejected | `#fce4ec` bg / `#c62828` text | `--bad` | Filled red chip |
| Needs Clarification | `#e3f2fd` bg / `#1565c0` text | `--info` | Filled blue chip |
| Resolved | `#f3e5f5` bg / `#7b1fa2` text | Muted purple | Outlined chip |
| Blocked | `#ffebee` bg / `#b71c1c` text | `--bad` | Solid red chip |

---

## 6. API/UI Mismatch Register

### 6.1 Missing Endpoints

| ID | Gap | Severity | Proposed Addition | Fallback |
|----|-----|----------|-------------------|----------|
| M-01 | No batch-level rollup counts in single endpoint | Medium | `GET /workspaces/{ws}/batches/rollups` — returns per-batch counts of patches, RFIs, corrections by status | Client-side: fetch queue + group by `batch_id` |
| M-02 | No analyst workload rollup endpoint | Medium | `GET /workspaces/{ws}/analyst-rollups` — returns per-analyst item counts | Client-side: fetch queue + group by `author_id` |
| M-03 | Batch health requires per-batch call | Low | Extend `GET /workspaces/{ws}/batches` to include inline health summary | Client-side: parallel fetch `GET /batches/{id}/health` for visible batches |
| M-04 | No aging/SLA metadata from server | Low | Add `oldest_pending_at` to batch rollups response | Client-side: compute from `created_at` on queue items |

### 6.2 Missing Payload Fields

| ID | Endpoint | Missing Field | Severity | Proposed | Fallback |
|----|----------|---------------|----------|----------|----------|
| F-01 | `GET /operations/queue` | `batch_name` on each item | Low | Join batches table to include `batch_name` | Client-side: maintain `batch_id → name` map from `/batches` |
| F-02 | `GET /operations/queue` | `age_bucket` computed field | Low | Add `age_bucket` to response items | Client-side: compute from `created_at` |
| F-03 | `GET /workspaces/{ws}/batches` | `item_counts` summary | Medium | Add `item_counts: { patches, rfis, corrections }` to batch list items | Separate fetch via queue endpoint |
| F-04 | `GET /operations/queue` counts | Per-batch breakdown | Medium | Add `counts_by_batch: { bat_id: { pending: N, ... } }` to response | Client-side: group items by batch_id |

### 6.3 Summary

- **No blockers.** All gaps have viable client-side fallbacks.
- **Recommended Phase 1 (P1):** Implement M-01 (batch rollups) and F-01 (batch_name on queue items) for performance — avoids N+1 fetches.
- **Defer to P2+:** M-02, M-03, M-04, F-02, F-03, F-04 — client-side computation is acceptable at current scale.

---

## 7. Acceptance Criteria (UI Readiness)

| # | Criterion | Test Method | Pass Condition |
|---|-----------|-------------|----------------|
| AC-01 | Role-correct visibility: org view hidden for analyst | Switch to analyst mode in sandbox | Org summary, batch table, workload panel all hidden |
| AC-02 | Role-correct visibility: org view visible for verifier | Switch to verifier mode | All panels render with data |
| AC-03 | Role-correct visibility: analyst workload panel shows detail for admin only | Switch between verifier and admin | Verifier sees aggregate; admin sees per-analyst |
| AC-04 | Queue-to-drilldown: click batch → filtered queue | Click a batch row | Queue items filter to that batch_id; URL updates |
| AC-05 | Queue-to-drilldown: click queue item → record detail | Click a queue row | Side panel opens with record inspector and evidence |
| AC-06 | Batch rollups: counts match queue data | Compare batch table counts to filtered queue counts | Numbers match (±0 tolerance) |
| AC-07 | Analyst rollups: counts match queue data (admin) | Compare analyst panel to filtered queue | Numbers match |
| AC-08 | Stale-version UX: 409 shows inline toast | Trigger concurrent edit (two tabs) | Toast shows "modified by another user", item not updated locally |
| AC-09 | Stale-version UX: bulk triage handles partial 409 | Bulk approve with one stale item | Summary toast shows N skipped, others complete |
| AC-10 | Sandbox parity: simulated verifier sees same as real verifier | Admin switches to verifier simulation | Same panels, same data scope |
| AC-11 | KPI click → filtered queue | Click "Pending" KPI counter | Queue filters to pending items, URL updates |
| AC-12 | Age buckets: correct color coding | Items at 0h, 36h, 96h age | Green, amber, red respectively |
| AC-13 | Empty state: no items | Empty workspace | "No batches with active items" message |
| AC-14 | Error state: server error | Simulate 500 response | Red banner with retry button |
| AC-15 | URL state persistence | Navigate to filtered view, refresh page | Filters preserved after reload |

---

## 8. QA Plan

### 8.1 Scenario Matrix

| # | Scenario | Setup | Steps | Expected |
|---|----------|-------|-------|----------|
| QA-01 | 5 analysts, mixed statuses | Create patches/RFIs from 5 different analyst users across 3 batches | Log in as verifier → open org view | All 5 analysts visible in workload panel; all 3 batches in batch table; KPI counts correct |
| QA-02 | Mixed custody states | RFIs in open, awaiting_verifier, returned_to_analyst, resolved | Open org view as verifier | Correct KPI breakdown; RFI custody badges match state |
| QA-03 | Concurrent verifier actions | Two verifier sessions open same queue | Both approve same patch simultaneously | First succeeds (200); second gets 409; second session shows toast and can refresh |
| QA-04 | Drive + upload batches | Create one drive batch, one upload batch | Open org view | Both appear in batch table; source badges correct (drive/upload); drive batch shows dedupe status |
| QA-05 | Batch drill-down → record detail | Navigate: org view → batch → record → evidence | Click through full hierarchy | Each level shows correct data; back navigation preserves parent filters |
| QA-06 | Analyst filter (admin) | Admin clicks specific analyst in workload panel | Queue filters to that analyst | Only that analyst's items shown; counts update; URL includes `analyst=usr_X` |
| QA-07 | Age bucket filter | Mix of items: 2h old, 36h old, 100h old | Click "72h+" age bucket | Only stale items shown; age badges red |
| QA-08 | Bulk approve | Select 5 pending patches | Click "Bulk Approve" | All 5 transition to Verifier_Approved; DB versions bumped; progress bar completes |
| QA-09 | Bulk approve with stale item | Select 5 patches; externally modify one | Click "Bulk Approve" | 4 succeed, 1 skipped; summary toast shows "4/5 approved, 1 skipped" |
| QA-10 | Role switch (sandbox) | Admin simulates analyst → verifier → admin | Switch roles in sandbox | Org view hidden as analyst, visible as verifier/admin; queue re-hydrates correctly; no stale data |

### 8.2 Smoke Steps (Quick Validation)

1. Log in as admin in sandbox mode
2. Navigate to `#/verifier-org`
3. Verify KPI strip shows non-zero counts
4. Click a batch row → queue filters to that batch
5. Click a queue item → side panel opens with record detail
6. Approve one item → status changes, version bumps, toast confirms
7. Switch to analyst role → org view hides
8. Switch back to verifier → org view re-appears with fresh data

---

## 9. Clarity Questions (Blocking Only)

| # | Question | Impact | Options |
|---|----------|--------|---------|
| CQ-01 | Should the org view be a new page/route (`#/verifier-org`) or replace the existing `#/verifier-review` triage? | IA decision — affects URL structure and navigation | **A)** New route (recommended — preserves existing verifier-review for deep single-item review) **B)** Replace existing triage |
| CQ-02 | Should analyst workload panel be visible to verifiers (aggregate only) or admin-only? | Privacy / role separation | **A)** Verifier sees aggregate workspace counts only, admin sees per-analyst (recommended) **B)** Hidden from verifier entirely |
| CQ-03 | SLA threshold: what is the aging boundary for "overdue"? | Determines amber/red bucketing | **A)** 72h (recommended based on typical turnaround) **B)** Configurable per workspace |
| CQ-04 | Should batch health data be fetched eagerly (on org view load) or lazily (on batch click)? | Performance vs. immediacy | **A)** Lazy — fetch on batch hover/click (recommended for workspaces with many batches) **B)** Eager — batch up to 10 parallel health calls on load |

---

## 10. Go/No-Go + Task Plan

### 10.1 Decision: GO for UI Implementation

**Rationale:**
- Backend is complete (P0–P3 hardened, role-scoped, custody transitions, drive dedupe)
- All existing API endpoints provide sufficient data for org view (with client-side fallbacks)
- No breaking changes required — additive UI only
- Mismatch register identifies performance optimizations (M-01, F-01) but no blockers

### 10.2 Task Plan

| Task ID | Phase | Description | Depends On | Estimate |
|---------|-------|-------------|------------|----------|
| VUI-01 | P0 | Scaffold `#/verifier-org` route and page container with zone layout | — | S |
| VUI-02 | P0 | Implement org summary strip (KPI counters from operations queue counts) | VUI-01 | S |
| VUI-03 | P0 | Implement KPI click → queue filter behavior + URL state sync | VUI-02 | M |
| VUI-04 | P1 | Implement batch queue table (fetch batches + client-side rollup) | VUI-01 | M |
| VUI-05 | P1 | Implement batch drill-down: click row → filter queue to batch | VUI-04 | M |
| VUI-06 | P1 | Implement drill-down side panel (record detail + evidence context) | VUI-05 | L |
| VUI-07 | P1 | Wire approve/reject/clarify actions from drill-down to DB write paths | VUI-06 | M |
| VUI-08 | P2 | Implement analyst workload panel (client-side rollup from queue) | VUI-01 | M |
| VUI-09 | P2 | Implement SLA/aging panel (client-side computed from created_at) | VUI-01 | S |
| VUI-10 | P2 | Implement risk/blocked panel (batch health aggregation) | VUI-04 | M |
| VUI-11 | P2 | Implement age bucket color-coding and badge rules | VUI-09 | S |
| VUI-12 | P3 | Implement bulk triage (select-all, bulk approve/reject) | VUI-07 | L |
| VUI-13 | P3 | Implement 409 stale-version UX (toast, skip-and-continue for bulk) | VUI-12 | M |
| VUI-14 | P3 | Implement empty/loading/error states for all zones | VUI-01 | M |
| VUI-15 | P3 | Implement permission-aware panel visibility (analyst/verifier/admin) | VUI-01 | S |
| VUI-16 | P3 | URL state persistence (hash params ↔ filter state ↔ dropdowns) | VUI-03 | M |
| VUI-17 | P4 | (API) Add `batch_name` join to operations queue response (F-01) | — | S |
| VUI-18 | P4 | (API) Add `GET /workspaces/{ws}/batches/rollups` endpoint (M-01) | — | M |
| VUI-19 | P4 | QA execution: run full scenario matrix (QA-01 through QA-10) | VUI-01..16 | L |
| VUI-20 | P4 | Dark mode integration: apply theme tokens to all org view elements | VUI-01..16 | M |

### 10.3 Dependency Graph

```
VUI-01 (scaffold)
  ├── VUI-02 (KPI strip) → VUI-03 (KPI click/URL)
  ├── VUI-04 (batch table) → VUI-05 (batch drill-down) → VUI-06 (side panel) → VUI-07 (actions)
  │                        → VUI-10 (risk/blocked)
  ├── VUI-08 (analyst workload)
  ├── VUI-09 (aging panel) → VUI-11 (age badges)
  ├── VUI-14 (empty/loading/error)
  └── VUI-15 (permission visibility)

VUI-07 → VUI-12 (bulk triage) → VUI-13 (stale-version UX)
VUI-03 → VUI-16 (URL persistence)
VUI-01..16 → VUI-19 (QA) + VUI-20 (dark mode)
VUI-17 + VUI-18 (API enhancements — can run parallel to UI work)
```

### 10.4 Phase Summary

| Phase | Tasks | Focus |
|-------|-------|-------|
| P0 | VUI-01, VUI-02, VUI-03 | Foundation: route, KPI strip, URL state |
| P1 | VUI-04, VUI-05, VUI-06, VUI-07 | Core: batch table, drill-down, actions |
| P2 | VUI-08, VUI-09, VUI-10, VUI-11 | Panels: analyst workload, aging, risk |
| P3 | VUI-12, VUI-13, VUI-14, VUI-15, VUI-16 | Polish: bulk triage, error handling, permissions, URL |
| P4 | VUI-17, VUI-18, VUI-19, VUI-20 | API enhancements, QA, dark mode |
