import logging
from datetime import datetime

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.api_v25 import envelope, collection_envelope, error_envelope
from server.auth import AuthClass, require_auth

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")

AUDIT_COLUMNS = [
    "id", "workspace_id", "event_type", "actor_id", "actor_role",
    "timestamp_iso", "dataset_id", "batch_id", "record_id", "field_key",
    "patch_id", "before_value", "after_value", "metadata",
]
AUDIT_SELECT = ", ".join(AUDIT_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/workspaces/{ws_id}/audit-events")
def list_audit_events(
    ws_id: str,
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    event_type: str = Query(None),
    actor_id: str = Query(None),
    patch_id: str = Query(None),
    batch_id: str = Query(None),
    record_id: str = Query(None),
    since: str = Query(None),
    until: str = Query(None),
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

            if event_type:
                conditions.append("event_type = %s")
                params.append(event_type)
            if actor_id:
                conditions.append("actor_id = %s")
                params.append(actor_id)
            if patch_id:
                conditions.append("patch_id = %s")
                params.append(patch_id)
            if batch_id:
                conditions.append("batch_id = %s")
                params.append(batch_id)
            if record_id:
                conditions.append("record_id = %s")
                params.append(record_id)
            if since:
                conditions.append("timestamp_iso >= %s")
                params.append(since)
            if until:
                conditions.append("timestamp_iso <= %s")
                params.append(until)
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM audit_events %s ORDER BY id ASC LIMIT %%s" % (AUDIT_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, AUDIT_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_audit_events error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/audit-events/{aud_id}")
def get_audit_event(
    aud_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM audit_events WHERE id = %%s" % AUDIT_SELECT,
                (aud_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Audit event not found: %s" % aud_id),
            )
        return envelope(_row_to_dict(row, AUDIT_COLUMNS))
    except Exception as e:
        logger.error("get_audit_event error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
