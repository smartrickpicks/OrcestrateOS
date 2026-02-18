# Preflight Integration Points

## Backend Integration

### Feature Flags (`server/feature_flags.py`)
- `PREFLIGHT_GATE_SYNC` — canonical flag constant
- `PREFLIGHT_GATE_SYNC_V251` — alias constant
- `is_preflight_enabled()` — checks canonical OR alias
- `require_preflight()` — gate check returning 404 error envelope if disabled

### Preflight Engine (`server/preflight_engine.py`)
Pure computation module. No DB, no HTTP, no side effects.
- `classify_page(chars, image_ratio)` → SEARCHABLE | SCANNED | MIXED
- `classify_document(page_modes)` → SEARCHABLE | SCANNED | MIXED
- `compute_text_metrics(pages_text)` → (replacement_ratio, control_ratio)
- `compute_gate(doc_mode, replacement, control, avg_chars, page_counts)` → (gate_color, reasons)
- `derive_cache_identity(workspace_id, file_url)` → deterministic doc_id
- `run_preflight(pages_data)` → full result dict

### API Routes (`server/routes/preflight.py`)
All routes share the same gate stack: auth → feature flag → workspace → admin sandbox RBAC.
- `POST /api/preflight/run` — external: run analysis
- `GET /api/preflight/{doc_id}` — external: read cached result
- `POST /api/preflight/action` — **internal**: Accept Risk / Escalate OCR

### PDF Text Layout (`server/pdf_proxy.py`)
- `GET /api/pdf/text_layout?url=...` — layout-aware text extraction with per-span bboxes, font info, and coord_space metadata

### Feature Flags Endpoint (`server/pdf_proxy.py`)
- `GET /api/v2.5/feature-flags` — includes `PREFLIGHT_GATE_SYNC` status in response

## Frontend Integration

### Feature Flag Fetch (`ui/viewer/index.html`)
On page load, the feature-flags fetch callback checks `PREFLIGHT_GATE_SYNC`. If true, calls `pfGateInit()` which:
1. Sets `_pfGateState.enabled = true`
2. Shows the Preflight tab button
3. Resolves current user role to set `adminOnly` flag

### Preflight State Object (`window._pfGateState`)
Canonical state read by all preflight UI and gating logic:
- `enabled` — feature flag on/off
- `running` — currently executing analysis
- `result` — last preflight result (gate_color, doc_mode, metrics, etc.)
- `actionTaken` — accept_risk | escalate_ocr | null
- `adminOnly` — true if current user is not admin/architect

### Submit Gating (`srrCheckSyncPreflightGate`)
Called by `validateSubmissionGates()`. Returns [] (no gaps) for:
- Feature disabled
- Non-admin users (adminOnly = true)
- GREEN gate
- YELLOW/RED gate with completed action

Returns blocking gaps for:
- Preflight not run (admin users only)
- YELLOW without action
- RED without escalation

### UI Panel Functions
- `pfGateInit()` — initialize on flag enable
- `pfGateTogglePanel()` — show/hide panel
- `pfGateRenderPanel()` — render gate badge, metrics, reason codes, action buttons
- `pfGateRun()` — call POST /api/preflight/run
- `pfGateAction(action)` — call POST /api/preflight/action

## Scope Boundary
POST /api/preflight/action is internal — it does not alter the locked external API contract. No schema changes, no migrations, no new database tables. Feature flags default OFF.
