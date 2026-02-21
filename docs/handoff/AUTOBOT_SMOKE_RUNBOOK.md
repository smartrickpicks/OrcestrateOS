# AutoBot Smoke Runbook

## Purpose
Validate the live AutoBot PRA chain against a running server without applying actions.

Script:
- `scripts/autobot_runtime_smoke.py`

This script calls:
1. `POST /api/v2.5/suggestion-runs/local`
2. `POST /api/preflight/run`
3. `POST /api/preflight/export`

It does **not** call `/api/preflight/action`.

## Prerequisites
- API server running and reachable (default `http://127.0.0.1:5000`).
- Valid Bearer token.
- Valid workspace id (`ws_...`).
- Reachable HTTP(S) PDF URL for `file_url`.

## Command
```bash
python3 scripts/autobot_runtime_smoke.py \
  --base-url "http://127.0.0.1:5000" \
  --token "<JWT>" \
  --workspace-id "ws_SEED0100000000000000000000" \
  --file-url "https://example.com/test.pdf" \
  --doc-id "autobot_smoke_doc"
```

Optional:
- `--source-field "Account Name"` (repeatable)
- `--body-text "..."`

## Expected Success Output
- Step 1 returns run id and suggestion count.
- Step 2 returns `gate_color` and `doc_id`.
- Step 3 returns `schema_version` and `preflight.recommended_gate`.
- Final line: `PASS: AutoBot runtime smoke completed (non-destructive).`

## Troubleshooting
- `FAILED suggestion run 400/422`:
  - Check `Authorization` and `X-Workspace-Id`.
  - Ensure at least one `source_field` or provide `--body-text`.
- `FAILED preflight run 400`:
  - Verify `file_url` is valid HTTP/HTTPS and reachable.
- `FAILED preflight run 403`:
  - Caller may not satisfy current preflight role gate.
- `FAILED preflight export 404`:
  - Ensure same `doc_id` is used and preflight run succeeded first.
- Network errors/timeouts:
  - Verify server base URL and local networking.

## Optional OpenAPI Contract Check
Use runtime schema check script:
```bash
python3 scripts/check_preflight_action_openapi.py --base-url "http://127.0.0.1:5000"
```
Expected:
- PASS line confirming `/api/preflight/action` includes:
  - `selected_action`
  - `latest_event.action_id`
  - `action_events_count`
  - expected action enum values
