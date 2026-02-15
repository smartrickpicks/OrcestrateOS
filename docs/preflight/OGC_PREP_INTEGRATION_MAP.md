# OGC Prep Simulator — Integration Map

## A. Repo Surface Inventory

### Backend Files

| File | Functions / Objects | Role | Touch Type |
|------|-------------------|------|------------|
| `server/routes/preflight.py` | `_preflight_cache`, `_cache_key()`, `_require_admin_sandbox()`, `_resolve_workspace()`, `_build_preflight_result()`, `preflight_run()`, `preflight_read()`, `preflight_action()` | All existing preflight API routes; cache storage and admin gating | **Modify**: Add `GET /export` endpoint; reuse `_preflight_cache` read, `_require_admin_sandbox`, `_resolve_workspace` |
| `server/preflight_engine.py` | `run_preflight()`, `classify_page()`, `classify_document()`, `compute_gate()`, `compute_text_metrics()`, `derive_cache_identity()` | Deterministic engine (locked thresholds) | **No change** — engine is not touched |
| `server/feature_flags.py` | `is_preflight_enabled()`, `require_preflight()`, `PREFLIGHT_GATE_SYNC` | Feature flag gating | **No change** — reuse existing flag |
| `server/auth.py` | `require_auth()`, `_apply_role_simulation()`, `resolve_auth()` | Auth + sandbox role simulation | **No change** — reuse existing patterns |
| `server/api_v25.py` | `envelope()`, `error_envelope()` | Response wrappers | **No change** — reuse |
| `server/db.py` | `get_conn()`, `put_conn()` | DB pool (not used for export, but available) | **No change** |
| `server/ulid.py` | `generate_id()` | ID generation | **No change** |

### Frontend Files

| File | Functions / Objects | Role | Touch Type |
|------|-------------------|------|------------|
| `ui/viewer/index.html` | `rerunPreFlight()` (line ~30311) | Run/Re-run Preflight button handler; clears triage state, re-runs batch PDF scan | **Modify**: Add modal trigger after scan completes |
| `ui/viewer/index.html` | `_p1fBatchPdfScan()` (line ~30422) | Batch PDF scan orchestrator; processes contracts with concurrency=3 | **Modify**: Hook completion to open Preflight Review Modal |
| `ui/viewer/index.html` | `_p1fScanSinglePdf()` (line ~30169) | Single PDF scan; calls `/api/pdf/text`, runs client-side quality checks | **No change** |
| `ui/viewer/index.html` | `_p1fScanState` (line ~27911) | Scan state object: running, totals, results per contract | **Read**: Export reads from this cache |
| `ui/viewer/index.html` | `preflightLiveState` (line ~27705) | Live intake accordion state: entries, order, totals | **Read**: Modal reads gate results from here |
| `ui/viewer/index.html` | `_p1fShowComplete()` (line ~30006) | Post-scan completion UI | **Modify**: Trigger Review Modal from here |
| `ui/viewer/index.html` | `_p1fUpdateBanner()` (line ~29974) | Progress banner during scan | **No change** |
| `ui/viewer/index.html` | `toolbarPdfPreflightUpload()` | Single PDF upload for Test Lab | **Modify**: Add modal trigger after single-doc preflight |
| `ui/viewer/index.html` | `_exportToFile()` (line ~23460) | Generic JSON export utility | **Reuse**: Pattern for Prep JSON download |
| `ui/viewer/index.html` | CSS classes `.preflight-*` (lines ~2018-2059) | Preflight UI styles | **Extend**: Add modal styles |
| `ui/viewer/index.html` | `showToast()` | Toast notification utility | **Reuse** |
| `ui/viewer/index.html` | `showModal()` / modal patterns | Generic modal rendering | **Reuse**: Pattern for Review Modal |

### Configuration Files

| File | Role | Touch Type |
|------|------|------------|
| `server/feature_flags.py` | `PREFLIGHT_GATE_SYNC` flag | **No change** — reuse existing |
| No new env vars needed | All behind existing flag | — |

## B. Reuse Points

| Component | Existing Code | Reuse For |
|-----------|--------------|-----------|
| Admin sandbox check | `_require_admin_sandbox()` in `server/routes/preflight.py:52` | Export endpoint admin gating |
| Workspace resolution | `_resolve_workspace()` in `server/routes/preflight.py:37` | Export endpoint workspace lookup |
| Preflight cache | `_preflight_cache` dict in `server/routes/preflight.py:34` | Export reads cached results |
| Cache key format | `_cache_key()` in `server/routes/preflight.py:67` | Export cache lookup |
| Feature flag gate | `require_preflight()` in `server/feature_flags.py:33` | Export endpoint feature check |
| Response wrappers | `envelope()` / `error_envelope()` in `server/api_v25.py` | Export response formatting |
| JSON export pattern | `_exportToFile()` in `ui/viewer/index.html:23460` | Client-side Prep JSON download |
| Preflight action API | `POST /api/preflight/action` | Accept Risk / Escalate OCR from modal |
| Toast notifications | `showToast()` | User feedback after modal actions |
| Batch scan results | `_p1fScanState.results` | Per-contract gate data for export |
| Scan completion hook | `_p1fShowComplete()` | Entry point for Review Modal |

## C. Blockers

**No blockers identified.**

All required infrastructure exists:
- Cache storage: `_preflight_cache` (server) + `_p1fScanState.results` (client)
- Admin gating: `_require_admin_sandbox()` with FORBIDDEN contract
- Action API: `POST /api/preflight/action` handles accept_risk / escalate_ocr
- Feature flags: `PREFLIGHT_GATE_SYNC` already controls all preflight routes
- Export pattern: `_exportToFile()` provides JSON download utility
- Modal pattern: Multiple existing modals in the UI provide rendering templates

## D. Risk Notes

1. **Server cache is in-memory** — `_preflight_cache` does not survive server restart. This is acceptable for v0 sandbox mode but should be documented for operators.
2. **Client-side OGC/evaluation state** — These are not persisted server-side. The export endpoint should accept them as POST body from the client, or the client assembles the full Prep JSON locally. Recommend client-side assembly for v0.
3. **Concurrency** — Multiple admins running preflight on the same doc_id will overwrite cached results. Acceptable for sandbox v0.
