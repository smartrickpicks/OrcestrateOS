import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.api_v25 import envelope, error_envelope
from server.auth import AuthClass, require_auth
from server.feature_flags import require_evidence_inspector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")


@router.get("/batches/{bat_id}/health")
def get_batch_health(
    bat_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth
    gate = require_evidence_inspector()
    if gate:
        return gate

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, workspace_id FROM batches WHERE id = %s AND deleted_at IS NULL", (bat_id,))
            batch_row = cur.fetchone()
            if not batch_row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Batch not found: %s" % bat_id),
                )
            workspace_id = batch_row[1]

            cur.execute(
                "SELECT COUNT(*) FROM rfis WHERE batch_id = %s "
                "AND deleted_at IS NULL AND (custody_status = 'open' OR (custody_status IS NULL AND status = 'open'))",
                (bat_id,),
            )
            rfis_open = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM rfis WHERE batch_id = %s "
                "AND deleted_at IS NULL AND (custody_status = 'awaiting_verifier' OR (custody_status IS NULL AND status = 'responded'))",
                (bat_id,),
            )
            rfis_awaiting = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM corrections WHERE document_id IN "
                "(SELECT id FROM documents WHERE batch_id = %s AND deleted_at IS NULL) "
                "AND deleted_at IS NULL AND status = 'pending_verifier'",
                (bat_id,),
            )
            corrections_pending = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM reader_node_cache WHERE document_id IN "
                "(SELECT id FROM documents WHERE batch_id = %s AND deleted_at IS NULL) "
                "AND quality_flag = 'suspect_mojibake'",
                (bat_id,),
            )
            mojibake_suspect = cur.fetchone()[0]

            cur.execute(
                "SELECT COUNT(*) FROM reader_node_cache WHERE document_id IN "
                "(SELECT id FROM documents WHERE batch_id = %s AND deleted_at IS NULL) "
                "AND quality_flag = 'unreadable'",
                (bat_id,),
            )
            reader_unreadable = cur.fetchone()[0]

            blockers = []
            if mojibake_suspect > 0:
                blockers.append("mojibake_suspect_docs: %d" % mojibake_suspect)
            if reader_unreadable > 0:
                blockers.append("reader_unreadable_docs: %d" % reader_unreadable)

        return envelope({
            "batch_id": bat_id,
            "counts": {
                "rfis_open": rfis_open,
                "rfis_awaiting_verifier": rfis_awaiting,
                "corrections_pending": corrections_pending,
                "mojibake_suspect_docs": mojibake_suspect,
                "reader_unreadable_docs": reader_unreadable,
            },
            "blockers": blockers,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        })
    except Exception as e:
        logger.error("get_batch_health error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
