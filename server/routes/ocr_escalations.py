import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.ulid import generate_id
from server.api_v25 import envelope, error_envelope
from server.auth import AuthClass, require_auth
from server.audit import emit_audit_event
from server.feature_flags import require_evidence_inspector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")

ESCALATION_COLUMNS = [
    "id", "document_id", "workspace_id", "escalation_type", "status",
    "requested_by", "resolved_by", "resolved_at",
    "created_at", "updated_at", "deleted_at", "version", "metadata",
]
ESCALATION_SELECT = ", ".join(ESCALATION_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.post("/documents/{doc_id}/ocr-escalations", status_code=201)
def create_ocr_escalation(
    doc_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth
    gate = require_evidence_inspector()
    if gate:
        return gate

    escalation_type = body.get("escalation_type", "ocr_reprocess")
    metadata = body.get("metadata", {})

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, workspace_id FROM documents WHERE id = %s AND deleted_at IS NULL",
                (doc_id,),
            )
            doc_row = cur.fetchone()
            if not doc_row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Document not found: %s" % doc_id),
                )
            workspace_id = doc_row[1]

            esc_id = generate_id("oce_")
            cur.execute(
                """INSERT INTO ocr_escalations
                   (id, document_id, workspace_id, escalation_type, status,
                    requested_by, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + ESCALATION_SELECT,
                (esc_id, doc_id, workspace_id, escalation_type, "pending",
                 auth.user_id, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="ocr_escalation.created",
                actor_id=auth.user_id,
                resource_type="ocr_escalation",
                resource_id=esc_id,
                detail={"document_id": doc_id, "escalation_type": escalation_type, "mock": True},
            )
        conn.commit()

        result = _row_to_dict(row, ESCALATION_COLUMNS)
        result["_mock"] = True
        result["_note"] = "OCR escalation recorded. Actual OCR reprocessing is not yet implemented."

        return JSONResponse(
            status_code=201,
            content=envelope(result),
        )
    except Exception as e:
        logger.error("create_ocr_escalation error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
