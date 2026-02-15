# Preflight Gate Sync — Overview

## Purpose
The Document Mode Preflight system analyzes PDF documents before patch submission to assess text quality, classify pages, and enforce quality gates.

## Current Stage
**Sandbox (Admin-only):** Preflight is currently enabled only for ADMIN role users when the preflight feature flag is on. Non-admin users cannot run preflight or trigger preflight persistence actions in this stage.

## Feature Flags
- Canonical: `PREFLIGHT_GATE_SYNC=true`
- Alias: `PREFLIGHT_GATE_SYNC_V251=true`
- Default: OFF

## Gate Colors
| Gate | Meaning | Action Required |
|------|---------|-----------------|
| GREEN | Document quality is good | None — submit freely |
| YELLOW | Borderline quality | Accept Risk or Escalate to OCR |
| RED | Document quality too low | Must Escalate to OCR |

## Key Components
- **Preflight Engine** (`server/preflight_engine.py`): Deterministic classification and gating logic
- **API Routes** (`server/routes/preflight.py`): POST /run, GET /{doc_id}, POST /action (internal)
- **UI Panel**: Preflight tab in float controls, gate display, action buttons (admin-only)
- **Submit Gating**: `validateSubmissionGates()` reads canonical preflight state; bypasses non-admin users during sandbox stage

## Invariants
- No schema changes, no migrations
- Feature flags default OFF
- All persistence is patch-based (not document-based), via `/patches/{id}/evidence-packs`
- POST /action is internal; it does not alter the locked external API contract
