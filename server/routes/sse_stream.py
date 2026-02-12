import json
import logging
import time
from datetime import datetime

from fastapi import APIRouter, Depends, Request, Query
from fastapi.responses import JSONResponse
from sse_starlette.sse import EventSourceResponse

from server.db import get_conn, put_conn
from server.api_v25 import error_envelope
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


def _sse_event_generator(ws_id, last_event_id, auth_user_id):
    last_id = last_event_id or ""
    poll_interval = 2

    while True:
        conn = get_conn()
        try:
            with conn.cursor() as cur:
                if last_id:
                    cur.execute(
                        "SELECT %s FROM audit_events WHERE workspace_id = %%s AND id > %%s ORDER BY id ASC LIMIT 50" % AUDIT_SELECT,
                        (ws_id, last_id),
                    )
                else:
                    cur.execute(
                        "SELECT %s FROM audit_events WHERE workspace_id = %%s ORDER BY id DESC LIMIT 10" % AUDIT_SELECT,
                        (ws_id,),
                    )
                rows = cur.fetchall()

                if not last_id and rows:
                    rows = list(reversed(rows))
        except Exception as e:
            logger.error("SSE poll error: %s", e)
            conn.rollback()
            put_conn(conn)
            time.sleep(poll_interval)
            continue
        finally:
            if conn:
                put_conn(conn)

        if rows:
            for row in rows:
                event_data = _row_to_dict(row, AUDIT_COLUMNS)
                event_id = event_data["id"]
                event_type = event_data.get("event_type", "audit")

                payload = {
                    "event_id": event_id,
                    "event_type": event_type,
                    "workspace_id": event_data.get("workspace_id"),
                    "actor_id": event_data.get("actor_id"),
                    "actor_role": event_data.get("actor_role"),
                    "timestamp_iso": event_data.get("timestamp_iso"),
                    "resource_type": _infer_resource_type(event_type),
                    "resource_id": _infer_resource_id(event_data),
                    "payload": {
                        k: v for k, v in event_data.items()
                        if k not in ("id", "workspace_id", "event_type", "actor_id", "actor_role", "timestamp_iso")
                        and v is not None
                    },
                }

                last_id = event_id
                yield {
                    "event": event_type,
                    "id": event_id,
                    "data": json.dumps(payload),
                }

        yield {"event": "heartbeat", "data": json.dumps({"ts": int(time.time())})}
        time.sleep(poll_interval)


def _infer_resource_type(event_type):
    if not event_type:
        return None
    parts = event_type.split(".")
    if len(parts) >= 1:
        return parts[0]
    return None


def _infer_resource_id(event_data):
    if event_data.get("patch_id"):
        return event_data["patch_id"]
    if event_data.get("batch_id"):
        return event_data["batch_id"]
    if event_data.get("record_id"):
        return event_data["record_id"]
    return None


@router.get("/workspaces/{ws_id}/events/stream")
async def sse_event_stream(
    request: Request,
    ws_id: str,
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
    finally:
        put_conn(conn)

    last_event_id = request.headers.get("Last-Event-ID")

    return EventSourceResponse(
        _sse_event_generator(ws_id, last_event_id, auth.user_id),
        media_type="text/event-stream",
    )
