# Replit Handoff: AutoBot FAB v1

## Scope
This handoff covers the shipped AutoBot FAB integration in the Viewer UI.

Included:
- FAB menu entry: `AutoBot`
- AutoBot panel with PRA sequence
- Safe endpoint chain only:
  - `POST /api/v2.5/suggestion-runs/local`
  - `POST /api/preflight/run`
  - `POST /api/preflight/export`
  - `POST /api/preflight/action`
- Header readiness guard (`Authorization`, `X-Workspace-Id`)
- RED gate policy in UI (`accept_risk` blocked/hidden)
- Runtime smoke and OpenAPI contract checks

Excluded:
- Dropbox/Drive/docs-suite logic
- New backend endpoints

## Pull Branch
```bash
git fetch origin
# If PR branch is known:
git checkout <branch-name>
# Or:
git checkout -b <branch-name> origin/<branch-name>
```

## Run Server
Use the repo's normal server startup path in Replit.
If running locally and your entrypoint is `server/pdf_proxy.py`, a common pattern is:
```bash
python3 server/pdf_proxy.py
```
Then confirm runtime OpenAPI:
```bash
curl -sS http://127.0.0.1:5000/openapi.json >/dev/null && echo "openapi ok"
```

## Run Smoke Script (Non-Destructive)
```bash
python3 scripts/autobot_runtime_smoke.py \
  --base-url "http://127.0.0.1:5000" \
  --token "<JWT>" \
  --workspace-id "ws_SEED0100000000000000000000" \
  --file-url "https://example.com/test.pdf" \
  --doc-id "autobot_smoke_doc"
```
Success looks like:
- suggestion run completes
- preflight returns `gate_color`
- export returns `schema_version`
- final `PASS` line

## Verify FAB AutoBot in Browser
1. Open Viewer page (`ui/viewer/index.html` runtime path).
2. Open FAB -> choose `AutoBot`.
3. Confirm status/stepper loads.
4. If headers missing, confirm run/apply disabled and error shown.
5. Click `Run AutoBot` and confirm step order:
   - Suggestion Run -> Preflight Run -> Export
6. Confirm results show: `gate_color`, `gate_reasons`, `decision_trace`, proposal summary, `action_events_count`.
7. Confirm `Copy Run Report` copies a JSON bundle with redacted authorization.
8. On RED gate, verify `accept_risk` is not available.

## OpenAPI Contract Check
```bash
python3 scripts/check_preflight_action_openapi.py --base-url "http://127.0.0.1:5000"
```
Expected:
- PASS
- action enum values present
- response fields present:
  - `selected_action`
  - `latest_event.action_id`
  - `action_events_count`

## Common Failure Modes
- Missing auth/workspace headers:
  - UI shows missing header error; run/apply disabled.
- `preflight/run` fails with missing `file_url`:
  - Ensure active document URL is available in viewer context.
- `preflight/export` 404:
  - `doc_id` mismatch or preflight run not completed in same workspace.
- `preflight/action` blocked on RED + `accept_risk`:
  - Expected gate behavior; choose allowed actions.
- Role/feature gate rejection (403/feature flag):
  - Validate environment role + preflight feature flag settings.
