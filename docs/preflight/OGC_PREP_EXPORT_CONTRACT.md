# OGC Prep JSON Export — API Contract

## Endpoint

```
GET /api/preflight/export?doc_id={doc_id}
```

**Auth**: v2.5 Either (Bearer or API Key)
**Gate**: `_require_admin_sandbox()` — admin/architect role required
**Feature flag**: `PREFLIGHT_GATE_SYNC` must be enabled

## Request

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| `doc_id` | query string | Yes | Document ID to export prep state for |

Workspace resolved via `X-Workspace-Id` header or auth-bound workspace.

## Response — Success (200)

```json
{
  "ok": true,
  "data": {
    "export_version": "prep_v0",
    "exported_at": "2026-02-15T12:00:00.000Z",
    "workspace_id": "ws_abc123",
    "doc_id": "doc_xyz789",
    "preflight": {
      "doc_mode": "SEARCHABLE",
      "gate_color": "GREEN",
      "gate_reasons": ["all_checks_passed"],
      "decision_trace": [ ... ],
      "corruption_samples": [ ... ],
      "page_classifications": [
        { "page": 1, "mode": "SEARCHABLE", "char_count": 1234, "image_coverage_ratio": 0.05 }
      ],
      "metrics": {
        "total_pages": 5,
        "total_chars": 12340,
        "avg_chars_per_page": 2468.0,
        "replacement_char_ratio": 0.0001,
        "control_char_ratio": 0.0,
        "mojibake_ratio": 0.0,
        "searchable_pages": 5,
        "scanned_pages": 0,
        "mixed_pages": 0
      },
      "action_taken": "accept_risk",
      "action_timestamp": "2026-02-15T11:58:00.000Z",
      "action_actor": "user_admin1",
      "materialized": false,
      "timestamp": "2026-02-15T11:55:00.000Z"
    },
    "ogc_preview": {
      "enabled": false,
      "toggled_at": null
    },
    "evaluation": {
      "ttt2_started_at": null,
      "ttt2_stopped_at": null,
      "confirmed": false,
      "precision": null,
      "coverage": null,
      "valid_for_rollup": false
    },
    "pipeline_state": "preflight_complete",
    "source": "cache"
  }
}
```

## Response — Cache Miss (404)

```json
{
  "ok": false,
  "error": {
    "code": "NOT_FOUND",
    "message": "No preflight result cached for doc_id: doc_xyz789"
  }
}
```

## Response — Not Admin (403)

```json
{
  "ok": false,
  "error": {
    "code": "FORBIDDEN",
    "message": "Preflight is in admin sandbox mode."
  }
}
```

## Response — Feature Disabled (404)

```json
{
  "ok": false,
  "error": {
    "code": "FEATURE_DISABLED",
    "message": "Preflight Gate Sync is not enabled. Set PREFLIGHT_GATE_SYNC=true to activate."
  }
}
```

## Determinism Guarantees

1. **No recompute** — Export reads directly from `_preflight_cache[workspace_id::doc_id]`. The preflight engine is never re-invoked during export.
2. **Idempotent** — Multiple calls with the same `doc_id` return the same result until a new `POST /api/preflight/run` replaces the cache entry.
3. **Cache lifetime** — In-memory; survives until server restart or explicit re-run.
4. **`source` field** — Always `"cache"` to signal this is a read from cached state, not a fresh computation.

## Pipeline State Values

| Value | Meaning |
|-------|---------|
| `preflight_pending` | No preflight run yet |
| `preflight_complete` | Preflight ran, no action taken |
| `preflight_accepted` | Accept Risk action taken (YELLOW gate) |
| `preflight_escalated` | Escalate OCR action taken |
| `preflight_cancelled` | User cancelled from RED modal |

## Notes

- `ogc_preview` and `evaluation` sections are populated from client-side state only; they are included in the export payload sent by the UI but not independently tracked server-side (no DB writes).
- The export endpoint may optionally accept a POST body with `ogc_preview` and `evaluation` state from the client if the server does not track these. This is documented as an alternative in the Integration Map.
