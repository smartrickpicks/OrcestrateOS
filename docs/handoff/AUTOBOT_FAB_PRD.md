# AutoBot FAB PRD

## Overview
AutoBot is a FAB menu option in the Viewer UI that runs the existing Airlock PRA sequence end-to-end and presents results in a review panel before any action is applied.

Runtime surface is unchanged:
- `POST /api/v2.5/suggestion-runs/local`
- `POST /api/preflight/run`
- `POST /api/preflight/export`
- `POST /api/preflight/action`

No Dropbox or Google Drive scope is included.

## Goals
- Add an operator-visible `AutoBot` entry in the FAB menu.
- Execute the PRA sequence in the client using existing endpoints.
- Show deterministic review outputs: gate color, reasons, decision trace, proposal summary, and action event count.
- Enforce header readiness (`Authorization`, `X-Workspace-Id`) before run/apply.
- Enforce RED policy in UI by hiding/blocking `accept_risk`.
- Keep a single in-memory run envelope to avoid cross-step ID drift.

## Non-Goals
- No new backend endpoints.
- No external storage/provider integrations (Dropbox/Drive/docs).
- No action graph orchestration changes.
- No persistent DB state for AutoBot UI (v1 is in-memory).

## UX States
- Ready:
  - Panel open, headers validated, `Run AutoBot` available.
- Running:
  - Stepper shows progress for:
    1. Suggestion Run
    2. Preflight Run
    3. Export
- Results:
  - Shows `gate_color`, `gate_reasons`, `decision_trace` (first items), proposal summary, and `action_events_count`.
- Action Picker:
  - Available actions filtered by gate color and policy.
  - RED does not allow `accept_risk`.
  - `Apply Action` triggers `/api/preflight/action` only after operator selection.

## PRA Call Chain
1. `POST /api/v2.5/suggestion-runs/local`
2. `POST /api/preflight/run` (requires `file_url`)
3. `POST /api/preflight/export` with `doc_id`
4. Optional: `POST /api/preflight/action` with `doc_id` + selected action

## Policy: Safe Internal Mutation
Allowed network actions for AutoBot:
- Read-like internal compute/export:
  - `POST /api/v2.5/suggestion-runs/local`
  - `POST /api/preflight/run`
  - `POST /api/preflight/export`
- Controlled internal mutation (explicit operator action only):
  - `POST /api/preflight/action`

Disallowed in this scope:
- Any Dropbox/Drive/docs provider interactions.
- Any additional write endpoints outside the list above.

## Acceptance Criteria
- FAB menu includes `AutoBot` and opens the AutoBot panel.
- Missing `Authorization` or `X-Workspace-Id` disables run/apply and shows clear error.
- `Run AutoBot` executes the 3-step sequence in order and renders results.
- `runEnvelope` is populated and reused for export/action `doc_id`.
- RED gate does not expose `accept_risk` in picker and blocks it client-side.
- `Apply Action` updates displayed `selected_action`, `latest_event`, and `action_events_count` from response.
- Non-destructive smoke script runs successfully without calling `/api/preflight/action`.
