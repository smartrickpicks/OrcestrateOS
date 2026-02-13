import hashlib
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.ulid import generate_id
from server.api_v25 import envelope, collection_envelope, error_envelope
from server.auth import AuthClass, require_auth
from server.audit import emit_audit_event
from server.feature_flags import require_evidence_inspector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")

ANCHOR_COLUMNS = [
    "id", "document_id", "workspace_id", "anchor_fingerprint",
    "node_id", "char_start", "char_end", "selected_text",
    "selected_text_hash",
    "field_id", "field_key", "page_number",
    "created_by", "created_at", "updated_at", "deleted_at", "version", "metadata",
]
ANCHOR_SELECT = ", ".join(ANCHOR_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


def _compute_selected_text_hash(selected_text):
    return hashlib.sha256((selected_text or "").encode("utf-8")).hexdigest()


def _compute_fingerprint(document_id, node_id, char_start, char_end, selected_text):
    text_hash = _compute_selected_text_hash(selected_text)
    raw = "%s|%s|%s|%s|%s" % (
        document_id or "",
        node_id or "",
        char_start if char_start is not None else "",
        char_end if char_end is not None else "",
        text_hash,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


@router.post("/documents/{doc_id}/anchors", status_code=201)
def create_anchor(
    doc_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth
    gate = require_evidence_inspector()
    if gate:
        return gate

    node_id = body.get("node_id")
    char_start = body.get("char_start")
    char_end = body.get("char_end")
    selected_text = body.get("selected_text")
    field_id = body.get("field_id")
    field_key = body.get("field_key")
    page_number = body.get("page_number")
    metadata = body.get("metadata", {})

    if not node_id:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "node_id is required"),
        )
    if char_start is None or char_end is None:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "char_start and char_end are required"),
        )
    if not selected_text:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "selected_text is required"),
        )

    selected_text_hash = _compute_selected_text_hash(selected_text)
    fingerprint = _compute_fingerprint(doc_id, node_id, char_start, char_end, selected_text)

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
                "SELECT %s FROM anchors WHERE anchor_fingerprint = %%s AND deleted_at IS NULL" % ANCHOR_SELECT,
                (fingerprint,),
            )
            existing = cur.fetchone()
            if existing:
                return JSONResponse(
                    status_code=200,
                    content=envelope(_row_to_dict(existing, ANCHOR_COLUMNS)),
                )

            anchor_id = generate_id("anc_")
            cur.execute(
                """INSERT INTO anchors
                   (id, document_id, workspace_id, anchor_fingerprint,
                    node_id, char_start, char_end, selected_text, selected_text_hash,
                    field_id, field_key, page_number, created_by, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + ANCHOR_SELECT,
                (anchor_id, doc_id, workspace_id, fingerprint,
                 node_id, char_start, char_end, selected_text, selected_text_hash,
                 field_id, field_key, page_number, auth.user_id,
                 json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="anchor.created",
                actor_id=auth.user_id,
                resource_type="anchor",
                resource_id=anchor_id,
                detail={
                    "document_id": doc_id,
                    "fingerprint": fingerprint,
                    "node_id": node_id,
                    "char_start": char_start,
                    "char_end": char_end,
                    "page_number": page_number,
                    "field_id": field_id,
                    "field_key": field_key,
                },
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, ANCHOR_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_anchor error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/documents/{doc_id}/anchors")
def list_anchors(
    doc_id: str,
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    include_deleted: bool = Query(False),
    field_id: str = Query(None),
    page_number: int = Query(None),
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

            conditions = ["document_id = %s"]
            params: list = [doc_id]
            if not include_deleted:
                conditions.append("deleted_at IS NULL")
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)
            if field_id:
                conditions.append("field_id = %s")
                params.append(field_id)
            if page_number is not None:
                conditions.append("page_number = %s")
                params.append(str(page_number))

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM anchors %s ORDER BY id ASC LIMIT %%s" % (ANCHOR_SELECT, where)
            params.append(str(limit + 1))

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, ANCHOR_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_anchors error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.delete("/anchors/{anchor_id}")
def delete_anchor(
    anchor_id: str,
    auth=Depends(require_auth(AuthClass.BEARER)),
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
                "SELECT id, deleted_at FROM anchors WHERE id = %s",
                (anchor_id,),
            )
            row = cur.fetchone()
            if not row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Anchor not found: %s" % anchor_id),
                )
            if row[1] is not None:
                return JSONResponse(
                    status_code=200,
                    content=envelope({"id": anchor_id, "deleted": True, "_already_deleted": True}),
                )

            cur.execute(
                "UPDATE anchors SET deleted_at = NOW() WHERE id = %s RETURNING id",
                (anchor_id,),
            )
        conn.commit()

        return JSONResponse(
            status_code=200,
            content=envelope({"id": anchor_id, "deleted": True}),
        )
    except Exception as e:
        logger.error("delete_anchor error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
