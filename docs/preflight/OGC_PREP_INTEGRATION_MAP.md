# OGC Prep Integration Map (Phase 1)

## 1) Canonical State (UI)
- `ui/viewer/index.html`
  `preflightSyncState` (authoritative sync preflight state object)
- `ui/viewer/index.html`
  `renderSyncPreflightPanel`
- `ui/viewer/index.html`
  `runSyncPreflight`

## 2) Preflight Server Cache/Routes
- `server/routes/preflight.py`
  - In-memory preflight cache (`_PREFLIGHT_CACHE`)
  - `POST /api/preflight/run`
  - `GET /api/preflight/{doc_id}`

## 3) Anchor/Highlight Reuse
- `ui/viewer/index.html` `eiRenderAnchors`
- `ui/viewer/index.html` `eiScrollToAnchor`
- `ui/viewer/index.html` `srrScrollToAnchor`
- `server/pdf_proxy.py`
  - anchor schema with `coord_space="pdf_points"` and page dims

## 4) PDF Endpoints (no recompute for export)
- `server/pdf_proxy.py` `GET /api/pdf/text`
- `server/pdf_proxy.py` `GET /api/pdf/text_layout`

## 5) Glossary/Alias/Ontology Context Sources
- `server/routes/glossary.py`
- `server/suggestion_engine.py`
- `rules/rules_bundle/field_meta.json`

## 6) Admin Sandbox Enforcement
- Existing preflight flag helpers:
  - `server/feature_flags.py`
- Existing auth mode patterns:
  - `server/auth.py`

## Notes
- This map is inventory only.
- Any endpoint additions are implementation-phase decisions and must stay under existing route families.
