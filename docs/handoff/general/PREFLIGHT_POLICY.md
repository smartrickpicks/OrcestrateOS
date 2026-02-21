# Preflight Policy

## Access Control Policy

### Current Stage: ADMIN-Only Sandbox
- Only users with ADMIN or ARCHITECT role may invoke preflight endpoints
- Non-admin callers receive: `code: FORBIDDEN`, `message: "Preflight is in admin sandbox mode."`
- This applies uniformly to all three endpoints:
  - `POST /api/preflight/run`
  - `GET /api/preflight/{doc_id}`
  - `POST /api/preflight/action`

### API Key Auth
API key authenticated requests bypass the role check. API keys are assumed to be issued only to authorized service accounts with admin-equivalent access. This is a policy constraint on key issuance, not a code-level role check.

### UI Policy
- Preflight tab is hidden for non-admin users
- If shown (e.g., via flag timing), non-admin users see "Admin-only sandbox." with no actionable controls
- Submit gating (`srrCheckSyncPreflightGate`) returns no gaps for non-admin users, preventing submission blocks on gates they cannot resolve

## Threshold Policy (Locked P1E)

### Page Classification
| Condition | Classification |
|-----------|---------------|
| chars >= 50 AND image_ratio <= 0.70 | SEARCHABLE |
| chars < 50 AND image_ratio >= 0.30 | SCANNED |
| All other combinations | MIXED |

### Document Mode Aggregation
- >= 80% pages SEARCHABLE → Document is SEARCHABLE
- >= 80% pages SCANNED → Document is SCANNED
- Otherwise → Document is MIXED

### Gate Colors
| Gate | Condition | Admin Action |
|------|-----------|-------------|
| RED | replacement_char_ratio > 0.05 OR control_char_ratio > 0.03 | Must Escalate to OCR |
| YELLOW | doc_mode MIXED OR avg_chars < 30 OR >80% sparse pages | Accept Risk or Escalate to OCR |
| GREEN | All checks pass | None required |

RED is evaluated first — it short-circuits before YELLOW checks.

## Persistence Policy
- Persistence is **patch-based**, not document-based
- Linkage path: `/patches/{patch_id}/evidence-packs`
- Two locked metadata keys written on patch-bound action:
  - `patch.metadata.preflight_summary`
  - `patch.metadata.system_evidence_pack_id`
- Without `patch_id`, actions are cache-only (no FK-bound writes)
- No database schema changes or migrations introduced

## Feature Flag Policy
- Canonical flag: `PREFLIGHT_GATE_SYNC` (default OFF)
- Alias: `PREFLIGHT_GATE_SYNC_V251` (default OFF)
- Either flag enables the feature
- Both must be explicitly set to `true` to activate
