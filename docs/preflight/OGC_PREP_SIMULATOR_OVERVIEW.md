# OGC Preparation Simulator — Overview

## Purpose

The OGC Preparation Simulator (v0) is an **admin-sandbox-only** feature that simulates the full document preparation pipeline within the Orchestrate OS UI, without introducing autonomous triggers, background jobs, or database schema changes. It allows admins to:

1. **Run/Re-run Preflight** on any document and optionally toggle OGC Preview visibility.
2. **Review Preflight Results** in a modal with gate-color-driven action paths (GREEN / YELLOW / RED).
3. **Simulate pipeline continuation** via UI state transitions (no server-side orchestration).
4. **Export a deterministic "Prep JSON"** from cached preflight + OGC state — never recomputing.

## Scope

| In Scope | Out of Scope |
|----------|-------------|
| Preflight Review Modal with gate-driven actions | DB schema changes / migrations |
| OGC Preview toggle (show/hide, no recompute) | Extraction / chunking / matching logic changes |
| Simulated pipeline state transitions (UI only) | Background / autonomous triggers / webhooks |
| Cached Prep JSON export | New feature flags (reuse `PREFLIGHT_GATE_SYNC`) |
| Admin-only sandbox enforcement | Non-admin access to simulator features |
| Evaluation carryover TTT-2 timing (if enabled) | Changes to submit gating (remains preflight-only) |

## Architecture Principles

1. **No autonomous behavior** — All compute happens on explicit user action (Run/Re-run Preflight button). Toggles are show/hide only.
2. **Cache-only export** — Prep JSON is assembled from `_preflight_cache[workspace_id::doc_id]` and `_p1fScanState.results[contract_id]` at export time. No recompute.
3. **Feature-flagged** — All new behavior is gated behind existing `PREFLIGHT_GATE_SYNC` flag, default OFF.
4. **Admin sandbox** — `_require_admin_sandbox()` enforces admin/architect role. Non-admin API calls return `{ code: "FORBIDDEN", message: "Preflight is in admin sandbox mode." }`. Non-admin UI hides/disables controls with "Admin-only sandbox." label.
5. **v2.5 patterns preserved** — All endpoints use `envelope()` / `error_envelope()`, existing auth decorators, and endpoint families under `/api/preflight/*`.

## User Flow

```
[Admin clicks "Run Preflight" on a document]
        │
        ▼
  POST /api/preflight/run  ← existing endpoint
        │
        ▼
  Engine runs, result cached in _preflight_cache
        │
        ▼
  Preflight Review Modal opens with gate color
        │
        ├── GREEN ──► "Continue" button ──► close modal, mark state as passed
        │
        ├── YELLOW ──► "Accept Risk" ──► POST /api/preflight/action {action: "accept_risk"}
        │              "Escalate OCR" ──► POST /api/preflight/action {action: "escalate_ocr"}
        │
        └── RED ──── "Escalate OCR" ──► POST /api/preflight/action {action: "escalate_ocr"}
                     "Cancel" ──► close modal, no state change
        │
        ▼
  [Optional] Toggle OGC Preview ON (show/hide only)
        │
        ▼
  [Export] GET /api/preflight/export?doc_id=X
        │
        ▼
  Returns deterministic Prep JSON from cache
```

## Evaluation Carryover (TTT-2)

When evaluation mode is enabled:

| Rule | Behavior |
|------|----------|
| TTT-2 start | First `OGC Preview OFF→ON` transition per doc session |
| TTT-2 stop | First valid "Confirm Patch-Ready Finding", then lock |
| Confirm disabled until | E1 + E2 + E3 conditions met + anchor + corrective intent |
| Precision/coverage | From operator-entered integers only |
| valid_for_rollup | `targets_labeled >= 5` |

## Non-Admin Behavior

- **API**: Returns HTTP 403 with `{ code: "FORBIDDEN", message: "Preflight is in admin sandbox mode." }`
- **UI**: All simulator controls hidden/disabled. Displays "Admin-only sandbox." label where controls would appear.
