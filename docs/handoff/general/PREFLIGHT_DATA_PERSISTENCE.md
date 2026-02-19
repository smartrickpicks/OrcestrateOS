# Preflight Data Persistence

## Cache Semantics
- Preflight results are cached in-memory, workspace-scoped
- Cache key: `{workspace_id}::{doc_id}`
- No database writes for preflight results (no schema changes, no migrations)

## RBAC Persistence Guard
Preflight persistence side-effects (Accept Risk / Escalate OCR) are **ADMIN-only** in the current sandbox stage. Non-admin callers are rejected with `code: FORBIDDEN`, `message: "Preflight is in admin sandbox mode."` and cannot create evidence-pack linkage updates or trigger escalation side-effects.

## Persistence Linkage: Patch-Based (Not Document-Based)
Preflight evidence packs are bound to **patches**, not documents. The linkage path is:

```
/patches/{patch_id}/evidence-packs
```

When `POST /api/preflight/action` receives a `patch_id`, it generates an evidence pack ID and writes two locked metadata keys to the patch:

1. `patch.metadata.preflight_summary` — deterministic snapshot of gate state at action time
2. `patch.metadata.system_evidence_pack_id` — the generated `evp_`-prefixed evidence pack ID

Without a `patch_id`, the action is cache-only (no FK-bound writes, no evidence pack linkage).

## Patch Metadata Keys (Locked)
```json
{
  "patch.metadata.preflight_summary": {
    "doc_id": "...",
    "gate_color": "YELLOW",
    "doc_mode": "MIXED",
    "action": "accept_risk",
    "metrics": { ... }
  },
  "patch.metadata.system_evidence_pack_id": "evp_..."
}
```

These keys are locked — no additional metadata keys are written by preflight actions.

## Non-Materialized Documents
- Skip FK-bound writes (no patch_id = no evidence pack)
- Still return full preflight payload
- Cache/session still written
- UI gating still enforced regardless of persistence state

## Schema and Migration Policy
- No database schema changes introduced by preflight
- No migration files created
- All persistence is cache-only until explicit patch-bound action
- Feature flags default OFF
