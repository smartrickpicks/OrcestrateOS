# OGC Prep Simulator (Phase 1: Documentation Only)

## Purpose
Define a deterministic, operator-visible preparation simulator output that shows exactly what would be sent downstream later, without triggering downstream automation.

## Scope
In scope:
- Exporting a single `prep_export_v0` JSON artifact from cached UI/server preflight state.
- Including cached preflight result, optional cached OGC preview, operator decisions, and optional evaluation block.
- Admin-only sandbox visibility and controls.

Out of scope:
- Any extraction/chunking/matching/model changes.
- Any DB schema change or migration.
- Any autonomous/background trigger/webhook.
- Any submit-gating change outside existing preflight gate logic.

## Determinism Rules
- Export is a snapshot of the cached preflight state currently used by UI.
- Export does not recompute preflight, OGC, PDF text, or layout.
- Stable field names and deterministic array ordering are required.

## Sandbox / RBAC
- Admin-only sandbox behavior remains mandatory.
- Non-admin users cannot run/export prep simulation and see `Admin-only sandbox.` in UI.

## Operator Flow (v0)
1. Open document context in existing viewer flow.
2. Run/Re-run preflight.
3. Optionally view OGC preview/highlights from cached results.
4. Choose gate action (`CONTINUE`, `ACCEPT_RISK`, `ESCALATE_OCR`, `CANCEL`) as simulation-only UI state.
5. Export or copy prep JSON from cached state.

## Verification Evidence (repo)
- Canonical preflight UI state:
  - `ui/viewer/index.html` (`preflightSyncState`)
  - `ui/viewer/index.html` (`renderSyncPreflightPanel`)
  - `ui/viewer/index.html` (`runSyncPreflight`)
- Anchor/viewer integration points:
  - `ui/viewer/index.html` (`eiRenderAnchors`)
  - `ui/viewer/index.html` (`eiScrollToAnchor`)
  - `ui/viewer/index.html` (`srrScrollToAnchor`)
- Selection payload hooks:
  - `ui/viewer/index.html` (`_evBindReaderSelection`)
  - `ui/viewer/index.html` (`_evGetSelectionPayload`)
- PDF extract/layout endpoints:
  - `server/pdf_proxy.py` (`GET /api/pdf/text`)
  - `server/pdf_proxy.py` (`GET /api/pdf/text_layout`)
- Glossary metadata source:
  - `rules/rules_bundle/field_meta.json`
