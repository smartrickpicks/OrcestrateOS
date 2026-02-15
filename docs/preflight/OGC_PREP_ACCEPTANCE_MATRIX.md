# OGC Prep Simulator — Acceptance Matrix

## AC-1: Preflight Review Modal

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 1.1 | Modal opens after batch scan completes | `_p1fShowComplete()` triggers modal with gate color from most recent scan |
| 1.2 | Modal opens after single-doc preflight upload | `toolbarPdfPreflightUpload()` completion triggers modal |
| 1.3 | Modal displays correct gate color | GREEN / YELLOW / RED badge matches `cached.gate_color` |
| 1.4 | Modal displays doc mode | SEARCHABLE / SCANNED / MIXED label matches `cached.doc_mode` |
| 1.5 | Modal displays metrics summary | total_pages, avg_chars_per_page, replacement_char_ratio visible |
| 1.6 | Decision trace is collapsible | Trace section expandable, shows rule/value/threshold/result per check |
| 1.7 | Corruption samples are collapsible | Samples section expandable, shows page/issue_type/snippet |

## AC-2: Gate-Driven Actions

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 2.1 | GREEN: "Continue" closes modal | Modal closes, `_prepSimState.pipeline = 'preflight_complete'`, toast shown |
| 2.2 | YELLOW: "Accept Risk" calls API | `POST /api/preflight/action {action: 'accept_risk'}` succeeds, `_prepSimState.pipeline = 'preflight_accepted'`, modal closes |
| 2.3 | YELLOW: "Escalate OCR" calls API | `POST /api/preflight/action {action: 'escalate_ocr'}` succeeds, `_prepSimState.pipeline = 'preflight_escalated'`, modal closes |
| 2.4 | RED: "Escalate OCR" calls API | Same as 2.3 |
| 2.5 | RED: "Cancel" closes modal | Modal closes, `_prepSimState.pipeline = 'preflight_cancelled'`, no API call |
| 2.6 | RED: "Accept Risk" not available | Button not rendered for RED gate |
| 2.7 | Action API rejects accept_risk on RED | Server returns 400 `GATE_BLOCKED` if someone bypasses UI |

## AC-3: OGC Preview Toggle

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 3.1 | Toggle is show/hide only | Toggling ON/OFF does not trigger any recompute or API call |
| 3.2 | State tracked | `_prepSimState.ogcPreview.enabled` and `toggled_at` reflect toggle state |
| 3.3 | OGC sections visibility | Relevant OGC UI sections show/hide based on toggle state |

## AC-4: Export Prep JSON

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 4.1 | Export uses cached result | No call to `run_preflight()` during export; reads from `_preflight_cache` |
| 4.2 | Export returns 404 on cache miss | `GET /api/preflight/export?doc_id=missing` returns 404 `NOT_FOUND` |
| 4.3 | Export JSON matches contract | Response shape matches `OGC_PREP_EXPORT_CONTRACT.md` |
| 4.4 | `source` field is "cache" | Always `"cache"` in export response |
| 4.5 | Idempotent reads | Multiple exports for same doc_id return identical results |
| 4.6 | Client download works | Browser downloads `.json` file via `_exportToFile()` pattern |
| 4.7 | Pipeline state included | `pipeline_state` field reflects `_prepSimState.pipeline` value |

## AC-5: Admin Sandbox Enforcement

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 5.1 | Non-admin API returns 403 | All preflight endpoints (including export) return `{ code: "FORBIDDEN", message: "Preflight is in admin sandbox mode." }` |
| 5.2 | Non-admin UI hides controls | Run Preflight, Export, OGC Toggle, Review Modal — all hidden for non-admin |
| 5.3 | Non-admin UI shows label | "Admin-only sandbox." displayed where controls would appear |
| 5.4 | sandbox_user bypasses | `sandbox_user` synthetic user passes admin check |
| 5.5 | API key bypasses | API key auth passes admin check |

## AC-6: No Autonomous Behavior

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 6.1 | No background jobs created | No setTimeout/setInterval that runs engine code without user click |
| 6.2 | No webhook triggers | No outbound HTTP calls triggered by state transitions |
| 6.3 | No DB writes from simulator | No INSERT/UPDATE to any table from prep simulator code paths |
| 6.4 | Toggle does not recompute | OGC Preview toggle changes visibility only; never calls `/api/preflight/run` |

## AC-7: Feature Flag Gating

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 7.1 | All endpoints gated | `require_preflight()` called before any logic in export endpoint |
| 7.2 | Default OFF | With no env var set, all simulator features are inaccessible |
| 7.3 | Flag name reused | Uses `PREFLIGHT_GATE_SYNC` — no new flag introduced |

## AC-8: Evaluation Carryover (if enabled)

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 8.1 | TTT-2 start recorded | Timestamp captured on first OGC Preview OFF→ON per doc session |
| 8.2 | TTT-2 stop recorded | Timestamp captured on first valid "Confirm Patch-Ready Finding" |
| 8.3 | Confirm disabled until conditions met | Button disabled until E1 + E2 + E3 + anchor + corrective intent |
| 8.4 | Precision/coverage are integers | Input fields accept integers only; no floats, no strings |
| 8.5 | valid_for_rollup threshold | `valid_for_rollup = true` only when `targets_labeled >= 5` |
| 8.6 | Lock after confirmation | After confirm, evaluation fields become read-only |

## AC-9: Submit Gating Unchanged

| # | Criterion | Pass Condition |
|---|-----------|---------------|
| 9.1 | Submit still preflight-only | Patch submit gating unchanged; evaluation/prep state does not gate submit |
| 9.2 | Existing submit flow unaffected | All existing submit validation paths remain identical |
