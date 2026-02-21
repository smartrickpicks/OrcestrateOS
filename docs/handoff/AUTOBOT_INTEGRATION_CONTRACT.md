# AutoBot Integration Contract

## Required Headers
All AutoBot API calls require:
- `Authorization: Bearer <JWT>`
- `X-Workspace-Id: ws_...`

## Runtime OpenAPI
- Runtime spec: `GET /openapi.json`
- Curated spec: `docs/api/openapi.yaml`

## Endpoint Contract

### 1) Suggestion Run (propose-only)
`POST /api/v2.5/suggestion-runs/local`

Request keys:
- `source_fields` (array of strings; can be empty if `body_text` provided)
- `document_id` (string)
- `body_text` (optional string)

Response keys (under envelope `data`):
- `id`
- `document_id`
- `total_suggestions`
- `diagnostics`
- `suggestions` (array)
- `suppressed` (array)

### 2) Preflight Run (deterministic gate)
`POST /api/preflight/run`

Request keys:
- `file_url` (HTTP/HTTPS string)
- `doc_id` (optional string)

Response keys (under envelope `data`):
- `doc_id`
- `gate_color` (`GREEN|YELLOW|RED`)
- `gate_reasons` (array)
- `decision_trace` (array)
- `metrics` (object)
- plus preflight analysis fields

### 3) Preflight Export (read-only export)
`POST /api/preflight/export`

Request keys:
- `doc_id` (string)

Response keys (under envelope `data`):
- `schema_version` (`prep_export_v0`)
- `context`
- `preflight` (includes recommended gate, reasons, trace)
- `ogc_preview`
- `operator_decisions`
- `evaluation`

### 4) Preflight Action (append-only action event)
`POST /api/preflight/action`

Request keys:
- `doc_id` (string, required)
- `action` (enum, required)
- `reason` (optional string; required by policy for `override_red`)
- `patch_id` (optional string)
- `reconstruction_review` (optional object; required for `reconstruction_complete`)
- `workspace_id` (optional string)

Action enum:
- `accept_risk`
- `generate_copy`
- `escalate_ocr`
- `override_red`
- `reconstruction_complete`

Response keys (under envelope `data`):
- `doc_id`
- `action`
- `gate_color`
- `health_score`
- `timestamp`
- `actor_id`
- `selected_action`
- `latest_event` (includes `action_id`, `at_utc`, `action`, `gate_reasons`, `decision_trace`)
- `action_events_count`

## RED Rule
Server policy:
- If gate is `RED`, `accept_risk` is rejected (`GATE_BLOCKED`).

UI policy:
- AutoBot action picker hides `accept_risk` for `RED` gate.
- AutoBot also guards client-side against submitting `accept_risk` on `RED`.

## AutoBot State Contract (UI)
AutoBot keeps a single in-memory `runEnvelope` with:
- `suggestion_run_id`
- `preflight_doc_id`
- `preflight_cache_id` (alias of `preflight_doc_id` in current implementation)
- `gate_color`, `gate_reasons`, `decision_trace`
- `export_blob`
- `selected_action`, `latest_event`, `action_events_count`

`runEnvelope.preflight_doc_id` is the source of truth for `/export` and `/action` request `doc_id`.
