# OGC Prep Simulator — Implementation Task List

## Phase 2 Tasks (Implementation)

### Task 1: Preflight Review Modal (UI)
**Files**: `ui/viewer/index.html`
**Estimate**: Medium

- Add HTML structure for Preflight Review Modal (`.prep-review-modal`)
- Modal content: gate color badge, doc mode, metrics summary, decision trace collapsible, corruption samples collapsible
- Gate-driven action buttons:
  - GREEN: "Continue" button — closes modal, updates `_prepSimState.pipeline = 'preflight_complete'`
  - YELLOW: "Accept Risk" button — calls `POST /api/preflight/action {action: 'accept_risk'}`, updates state, closes modal
  - YELLOW: "Escalate OCR" button — calls `POST /api/preflight/action {action: 'escalate_ocr'}`, updates state, closes modal
  - RED: "Escalate OCR" button — same as YELLOW
  - RED: "Cancel" button — closes modal, sets `_prepSimState.pipeline = 'preflight_cancelled'`
- Add CSS styles extending existing `.preflight-*` classes
- Wire `showToast()` for action confirmation
- Non-admin guard: check user role before rendering; show "Admin-only sandbox." if non-admin

### Task 2: Modal Entry Points (UI)
**Files**: `ui/viewer/index.html`
**Estimate**: Small

- Hook into `_p1fShowComplete()` (line ~30006): after batch scan completes, open Review Modal for the most recently scanned or user-selected contract
- Hook into `toolbarPdfPreflightUpload()`: after single-doc preflight run, open Review Modal for that document
- Hook into `rerunPreFlight()` completion callback: trigger modal after re-run
- Ensure modal only opens for admin users (check role before triggering)

### Task 3: OGC Preview Toggle (UI)
**Files**: `ui/viewer/index.html`
**Estimate**: Small

- Add "OGC Preview" toggle switch in the Preflight Review Modal or toolbar area
- Toggle is show/hide only — does NOT trigger any recompute
- Track toggle state in `_prepSimState.ogcPreview = { enabled: bool, toggled_at: timestamp|null }`
- If evaluation carryover is enabled, record TTT-2 start on first OFF→ON transition per doc session
- Toggle visibility of OGC-related UI sections based on state

### Task 4: Prep Simulator State Object (UI)
**Files**: `ui/viewer/index.html`
**Estimate**: Small

- Create `_prepSimState` object:
  ```javascript
  var _prepSimState = {
    pipeline: 'preflight_pending',  // preflight_pending | preflight_complete | preflight_accepted | preflight_escalated | preflight_cancelled
    ogcPreview: { enabled: false, toggled_at: null },
    evaluation: {
      ttt2_started_at: null,
      ttt2_stopped_at: null,
      confirmed: false,
      precision: null,
      coverage: null,
      valid_for_rollup: false,
      targets_labeled: 0
    },
    activeDocId: null,
    activeWorkspaceId: null
  };
  ```
- Reset on new document selection or re-run
- State transitions driven by modal actions only

### Task 5: Evaluation Carryover Logic (UI)
**Files**: `ui/viewer/index.html`
**Estimate**: Small-Medium

- TTT-2 start: record timestamp on first OGC Preview OFF→ON transition per doc session
- TTT-2 stop: record timestamp on first valid "Confirm Patch-Ready Finding"
- "Confirm" button disabled until: E1 + E2 + E3 conditions met + anchor exists + corrective intent present
- Precision/coverage fields: operator-entered integers only (input validation)
- `valid_for_rollup = targets_labeled >= 5`
- Lock evaluation state after confirmation (disable further edits)

### Task 6: Prep JSON Export — Server Endpoint
**Files**: `server/routes/preflight.py`
**Estimate**: Small

- Add `GET /api/preflight/export` endpoint
- Auth: `require_auth(AuthClass.EITHER)` + `require_preflight()` + `_require_admin_sandbox()`
- Query param: `doc_id` (required)
- Reads from `_preflight_cache[workspace_id::doc_id]` — no recompute
- Returns 404 if cache miss
- Response shape per `OGC_PREP_EXPORT_CONTRACT.md`
- `source` field always `"cache"`
- Optionally accept POST body with client-side `ogc_preview` and `evaluation` state to merge into export

### Task 7: Prep JSON Export — Client Integration (UI)
**Files**: `ui/viewer/index.html`
**Estimate**: Small

- Add "Export Prep JSON" button in Review Modal footer or toolbar
- Button assembles Prep JSON from:
  - Cached preflight result (from `_p1fScanState.results[contractId]` or fetched via `GET /api/preflight/{doc_id}`)
  - `_prepSimState.ogcPreview`
  - `_prepSimState.evaluation`
  - `_prepSimState.pipeline`
- Uses `_exportToFile()` pattern for browser download
- Alternative: POST to `/api/preflight/export` with client state, receive assembled JSON
- Admin-only: button hidden for non-admin users

### Task 8: Non-Admin UI Guards
**Files**: `ui/viewer/index.html`
**Estimate**: Small

- Wrap all simulator UI controls with admin role check
- Non-admin: hide "Run Preflight", "Export Prep JSON", OGC Preview toggle
- Show "Admin-only sandbox." label where controls would appear
- Ensure modal cannot be opened by non-admin users

## Dependency Order

```
Task 4 (State Object)
  └── Task 1 (Review Modal)
        ├── Task 2 (Modal Entry Points)
        ├── Task 3 (OGC Preview Toggle)
        │     └── Task 5 (Evaluation Carryover)
        └── Task 7 (Client Export)
Task 6 (Server Export Endpoint) — independent
Task 8 (Non-Admin Guards) — after Tasks 1-3
```

## Total Estimate

~7-8 focused implementation steps. No database migrations. No new feature flags. All behind existing `PREFLIGHT_GATE_SYNC` gate.
