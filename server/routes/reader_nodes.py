import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.api_v25 import envelope, error_envelope
from server.auth import AuthClass, require_auth
from server.feature_flags import require_evidence_inspector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/documents/{doc_id}/reader-nodes")
def get_reader_nodes(
    doc_id: str,
    source_pdf_hash: str = Query(None),
    ocr_version: str = Query("v1"),
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
            cur.execute(
                "SELECT id FROM documents WHERE id = %s AND deleted_at IS NULL",
                (doc_id,),
            )
            if not cur.fetchone():
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Document not found: %s" % doc_id),
                )

            if source_pdf_hash:
                cur.execute(
                    """SELECT id, document_id, source_pdf_hash, ocr_version,
                              quality_flag, nodes, page_count, created_at, metadata
                       FROM reader_node_cache
                       WHERE document_id = %s AND source_pdf_hash = %s AND ocr_version = %s""",
                    (doc_id, source_pdf_hash, ocr_version),
                )
                row = cur.fetchone()
                if row:
                    cols = ["id", "document_id", "source_pdf_hash", "ocr_version",
                            "quality_flag", "nodes", "page_count", "created_at", "metadata"]
                    return envelope(_row_to_dict(row, cols))

            return envelope({
                "document_id": doc_id,
                "nodes": [],
                "quality_flag": "missing_text_layer",
                "page_count": 0,
                "cached": False,
            })
    except Exception as e:
        logger.error("get_reader_nodes error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
