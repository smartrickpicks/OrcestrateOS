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

SIGNAL_COLUMNS = [
    "id", "workspace_id", "batch_id", "record_id", "field_key",
    "signal_type", "severity", "rule_id", "message", "created_at", "metadata",
]
SIGNAL_SELECT = ", ".join(SIGNAL_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/batches/{bat_id}/signals")
def list_signals(
    bat_id: str,
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
                "SELECT id, workspace_id FROM batches WHERE id = %s AND deleted_at IS NULL",
                (bat_id,),
            )
            batch_row = cur.fetchone()
            if not batch_row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Batch not found: %s" % bat_id),
                )

            conditions = ["batch_id = %s"]
            params = [bat_id]

            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM signals %s ORDER BY id ASC LIMIT %%s" % (SIGNAL_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, SIGNAL_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_signals error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/batches/{bat_id}/signals", status_code=201)
def create_signal(
    bat_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    record_id = body.get("record_id")
    if not record_id or not isinstance(record_id, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "record_id is required and must be a string"),
        )

    field_key = body.get("field_key")
    if not field_key or not isinstance(field_key, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "field_key is required and must be a string"),
        )

    signal_type = body.get("signal_type")
    if not signal_type or not isinstance(signal_type, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "signal_type is required and must be a string"),
        )

    severity = body.get("severity")
    if not severity or not isinstance(severity, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "severity is required and must be a string"),
        )

    message = body.get("message")
    if not message or not isinstance(message, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "message is required and must be a string"),
        )

    rule_id = body.get("rule_id")
    metadata = body.get("metadata", {})
    sig_id = generate_id("sig_")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, workspace_id FROM batches WHERE id = %s AND deleted_at IS NULL",
                (bat_id,),
            )
            batch_row = cur.fetchone()
            if not batch_row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Batch not found: %s" % bat_id),
                )
            workspace_id = batch_row[1]

            cur.execute(
                """INSERT INTO signals
                   (id, workspace_id, batch_id, record_id, field_key,
                    signal_type, severity, rule_id, message, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + SIGNAL_SELECT,
                (sig_id, workspace_id, bat_id, record_id, field_key,
                 signal_type, severity, rule_id, message, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="signal.created",
                actor_id=auth.user_id,
                resource_type="signal",
                resource_id=sig_id,
                batch_id=bat_id,
                record_id=record_id,
                field_key=field_key,
                detail={"signal_type": signal_type, "severity": severity},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, SIGNAL_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_signal error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/signals/{sig_id}")
def get_signal(
    sig_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM signals WHERE id = %%s" % SIGNAL_SELECT,
                (sig_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Signal not found: %s" % sig_id),
            )
        return envelope(_row_to_dict(row, SIGNAL_COLUMNS))
    except Exception as e:
        logger.error("get_signal error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
