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

ANNOTATION_COLUMNS = [
    "id", "workspace_id", "author_id", "target_type", "target_id",
    "content", "annotation_type", "created_at", "updated_at",
    "deleted_at", "version", "metadata",
]
ANNOTATION_SELECT = ", ".join(ANNOTATION_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/workspaces/{ws_id}/annotations")
def list_annotations(
    ws_id: str,
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    include_deleted: bool = Query(False),
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM workspaces WHERE id = %s AND deleted_at IS NULL", (ws_id,))
            if not cur.fetchone():
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Workspace not found: %s" % ws_id),
                )

            conditions = ["workspace_id = %s"]
            params = [ws_id]

            if not include_deleted:
                conditions.append("deleted_at IS NULL")
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM annotations %s ORDER BY id ASC LIMIT %%s" % (ANNOTATION_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, ANNOTATION_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_annotations error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/workspaces/{ws_id}/annotations", status_code=201)
def create_annotation(
    ws_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    target_type = body.get("target_type")
    target_id = body.get("target_id")
    content = body.get("content")

    if not target_type or not isinstance(target_type, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "target_type is required and must be a string"),
        )
    if not target_id or not isinstance(target_id, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "target_id is required and must be a string"),
        )
    if not content or not isinstance(content, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "content is required and must be a string"),
        )

    annotation_type = body.get("annotation_type", "note")
    metadata = body.get("metadata", {})
    ann_id = generate_id("ann_")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM workspaces WHERE id = %s AND deleted_at IS NULL", (ws_id,))
            if not cur.fetchone():
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Workspace not found: %s" % ws_id),
                )

            cur.execute(
                """INSERT INTO annotations
                   (id, workspace_id, author_id, target_type, target_id,
                    content, annotation_type, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + ANNOTATION_SELECT,
                (ann_id, ws_id, auth.user_id, target_type, target_id,
                 content, annotation_type, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="annotation.created",
                actor_id=auth.user_id,
                resource_type="annotation",
                resource_id=ann_id,
                detail={"target_type": target_type, "target_id": target_id},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, ANNOTATION_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_annotation error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/annotations/{ann_id}")
def get_annotation(
    ann_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM annotations WHERE id = %%s AND deleted_at IS NULL" % ANNOTATION_SELECT,
                (ann_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Annotation not found: %s" % ann_id),
            )
        return envelope(_row_to_dict(row, ANNOTATION_COLUMNS))
    except Exception as e:
        logger.error("get_annotation error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/annotations/{ann_id}")
def update_annotation(
    ann_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    version = body.get("version")
    if version is None or not isinstance(version, int):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "version (integer) is required for PATCH"),
        )

    updates = {}
    if "content" in body:
        updates["content"] = body["content"]
    if "annotation_type" in body:
        updates["annotation_type"] = body["annotation_type"]
    if "target_type" in body:
        updates["target_type"] = body["target_type"]
    if "target_id" in body:
        updates["target_id"] = body["target_id"]
    if "metadata" in body:
        updates["metadata"] = body["metadata"]

    if not updates:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "No updatable fields provided"),
        )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT version, deleted_at, workspace_id FROM annotations WHERE id = %s",
                (ann_id,),
            )
            row = cur.fetchone()
            if not row or row[1] is not None:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Annotation not found: %s" % ann_id),
                )

            current_version = row[0]
            workspace_id = row[2]
            if current_version != version:
                return JSONResponse(
                    status_code=409,
                    content=error_envelope(
                        "STALE_VERSION",
                        "Resource has been modified since your last read",
                        details={"current_version": current_version, "provided_version": version},
                    ),
                )

            set_clauses = []
            params = []
            for k, v in updates.items():
                if k == "metadata":
                    set_clauses.append("metadata = %s::jsonb")
                    params.append(json.dumps(v))
                else:
                    set_clauses.append("%s = %%s" % k)
                    params.append(v)
            set_clauses.append("version = version + 1")
            set_clauses.append("updated_at = NOW()")

            params.extend([ann_id, version])
            sql = "UPDATE annotations SET %s WHERE id = %%s AND version = %%s RETURNING %s" % (
                ", ".join(set_clauses),
                ANNOTATION_SELECT,
            )
            cur.execute(sql, params)
            updated = cur.fetchone()

            if not updated:
                conn.rollback()
                return JSONResponse(
                    status_code=409,
                    content=error_envelope("STALE_VERSION", "Concurrent modification detected"),
                )

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="annotation.updated",
                actor_id=auth.user_id,
                resource_type="annotation",
                resource_id=ann_id,
                detail={"fields": list(updates.keys()), "new_version": version + 1},
            )
        conn.commit()
        return envelope(_row_to_dict(updated, ANNOTATION_COLUMNS))
    except Exception as e:
        logger.error("update_annotation error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
