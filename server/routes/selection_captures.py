import json
import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.ulid import generate_id
from server.api_v25 import envelope, collection_envelope, error_envelope
from server.auth import AuthClass, require_auth
from server.audit import emit_audit_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")

ALLOWED_PURPOSES = ("evidence", "annotation", "rfi_anchor")

SELCAP_COLUMNS = [
    "id", "workspace_id", "author_id", "document_id", "field_id",
    "rfi_id", "page_number", "coordinates", "selected_text",
    "purpose", "created_at", "metadata",
]
SELCAP_SELECT = ", ".join(SELCAP_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/documents/{doc_id}/selection-captures")
def list_selection_captures(
    doc_id: str,
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

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

            conditions = ["document_id = %s"]
            params = [doc_id]

            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM selection_captures %s ORDER BY id ASC LIMIT %%s" % (SELCAP_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, SELCAP_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_selection_captures error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/documents/{doc_id}/selection-captures", status_code=201)
def create_selection_capture(
    doc_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    purpose = body.get("purpose")
    if purpose not in ALLOWED_PURPOSES:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "purpose must be one of: %s" % ", ".join(ALLOWED_PURPOSES)),
        )

    field_id = body.get("field_id")
    rfi_id = body.get("rfi_id")
    page_number = body.get("page_number")
    coordinates = body.get("coordinates")
    selected_text = body.get("selected_text")
    metadata = body.get("metadata", {})
    sel_id = generate_id("sel_")

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

            cur.execute(
                """INSERT INTO selection_captures
                   (id, workspace_id, author_id, document_id, field_id,
                    rfi_id, page_number, coordinates, selected_text, purpose, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + SELCAP_SELECT,
                (sel_id, workspace_id, auth.user_id, doc_id, field_id,
                 rfi_id, page_number,
                 json.dumps(coordinates) if coordinates is not None else None,
                 selected_text, purpose, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="selection_capture.created",
                actor_id=auth.user_id,
                resource_type="selection_capture",
                resource_id=sel_id,
                detail={"purpose": purpose, "document_id": doc_id},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, SELCAP_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_selection_capture error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/selection-captures/{sel_id}")
def get_selection_capture(
    sel_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM selection_captures WHERE id = %%s" % SELCAP_SELECT,
                (sel_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Selection capture not found: %s" % sel_id),
            )
        return envelope(_row_to_dict(row, SELCAP_COLUMNS))
    except Exception as e:
        logger.error("get_selection_capture error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
