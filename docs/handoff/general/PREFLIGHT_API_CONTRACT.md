# Preflight API Contract

## Authentication
All `/api/preflight/*` endpoints require v2.5 Either auth (Bearer token or API key).

## Admin Sandbox RBAC
`/api/preflight/*` requires ADMIN role in addition to feature-flag enablement.

If caller is non-admin, return v2.5 error envelope:
- code: `FORBIDDEN`
- message: `"Preflight is in admin sandbox mode."`

This applies to:
- `POST /api/preflight/run`
- `GET /api/preflight/{doc_id}`
- `POST /api/preflight/action`

## Endpoints

### POST /api/preflight/run
Run preflight analysis on a document.

**Request:**
```json
{
  "file_url": "https://...",
  "doc_id": "optional_doc_id"
}
```

**Headers:** Authorization (Bearer/API key), X-Workspace-Id (fallback)

**Response (200):**
```json
{
  "data": {
    "doc_id": "...",
    "workspace_id": "...",
    "doc_mode": "SEARCHABLE|SCANNED|MIXED",
    "gate_color": "GREEN|YELLOW|RED",
    "gate_reasons": ["..."],
    "page_classifications": [...],
    "metrics": {
      "total_pages": 10,
      "avg_chars_per_page": 1234.5,
      "replacement_char_ratio": 0.001,
      "control_char_ratio": 0.0005,
      "searchable_pages": 8,
      "scanned_pages": 1,
      "mixed_pages": 1
    },
    "materialized": false,
    "timestamp": "..."
  }
}
```

### GET /api/preflight/{doc_id}
Read cached preflight result.

### POST /api/preflight/action (Internal)
**Internal endpoint.** Handles Accept Risk or Escalate OCR actions. This endpoint is classified as internal — it does not alter the locked external API contract surface. It is consumed only by the preflight UI panel and is not part of the external-facing API.

**RBAC:** Same admin-only sandbox gate as `/run` and `/{doc_id}`.

**Request:**
```json
{
  "doc_id": "...",
  "action": "accept_risk|escalate_ocr",
  "patch_id": "optional — when present, triggers patch-based evidence pack linkage"
}
```

**Persistence semantics:**
- Without `patch_id`: Cache-only, no FK-bound writes
- With `patch_id`: Generates `evp_`-prefixed evidence pack ID, writes `patch.metadata.preflight_summary` and `patch.metadata.system_evidence_pack_id` to `/patches/{patch_id}/evidence-packs`

**Gate enforcement:**
- `accept_risk` on RED gate returns `400 GATE_BLOCKED`
- `accept_risk` on YELLOW gate is allowed
- `escalate_ocr` is allowed on both YELLOW and RED gates

## Workspace Resolution
1. Auth-resolved workspace first
2. Fallback: X-Workspace-Id header
3. Body field: workspace_id

## Derived Cache Identity
When doc_id is missing: `doc_derived_<sha256(workspace_id + file_url)[:24]>`
