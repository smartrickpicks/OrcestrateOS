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

ALLOWED_SEVERITIES = ("info", "warning", "blocker")
ALLOWED_SOURCES = ("qa_rule", "preflight", "system_pass", "manual")
ALLOWED_STATUSES = ("open", "in_review", "resolved", "dismissed")

TRIAGE_COLUMNS = [
    "id", "workspace_id", "batch_id", "record_id", "field_key",
    "issue_type", "severity", "source", "status", "resolved_by",
    "resolved_at", "created_at", "updated_at", "deleted_at", "version", "metadata",
]
TRIAGE_SELECT = ", ".join(TRIAGE_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/batches/{bat_id}/triage-items")
def list_triage_items(
    bat_id: str,
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

            if not include_deleted:
                conditions.append("deleted_at IS NULL")
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM triage_items %s ORDER BY id ASC LIMIT %%s" % (TRIAGE_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, TRIAGE_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_triage_items error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/batches/{bat_id}/triage-items", status_code=201)
def create_triage_item(
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

    issue_type = body.get("issue_type")
    if not issue_type or not isinstance(issue_type, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "issue_type is required and must be a string"),
        )

    severity = body.get("severity")
    if severity not in ALLOWED_SEVERITIES:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "severity must be one of: %s" % ", ".join(ALLOWED_SEVERITIES)),
        )

    source = body.get("source")
    if source not in ALLOWED_SOURCES:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "source must be one of: %s" % ", ".join(ALLOWED_SOURCES)),
        )

    field_key = body.get("field_key")
    status = body.get("status", "open")
    if status not in ALLOWED_STATUSES:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "status must be one of: %s" % ", ".join(ALLOWED_STATUSES)),
        )
    metadata = body.get("metadata", {})
    tri_id = generate_id("tri_")

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
                """INSERT INTO triage_items
                   (id, workspace_id, batch_id, record_id, field_key,
                    issue_type, severity, source, status, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + TRIAGE_SELECT,
                (tri_id, workspace_id, bat_id, record_id, field_key,
                 issue_type, severity, source, status, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="triage_item.created",
                actor_id=auth.user_id,
                resource_type="triage_item",
                resource_id=tri_id,
                batch_id=bat_id,
                record_id=record_id,
                detail={"issue_type": issue_type, "severity": severity, "source": source},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, TRIAGE_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_triage_item error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/triage-items/{tri_id}")
def get_triage_item(
    tri_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM triage_items WHERE id = %%s AND deleted_at IS NULL" % TRIAGE_SELECT,
                (tri_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Triage item not found: %s" % tri_id),
            )
        return envelope(_row_to_dict(row, TRIAGE_COLUMNS))
    except Exception as e:
        logger.error("get_triage_item error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/triage-items/{tri_id}")
def update_triage_item(
    tri_id: str,
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
    if "status" in body:
        if body["status"] not in ALLOWED_STATUSES:
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "status must be one of: %s" % ", ".join(ALLOWED_STATUSES)),
            )
        updates["status"] = body["status"]
        if body["status"] in ("resolved", "dismissed"):
            updates["resolved_by"] = auth.user_id
    if "severity" in body:
        if body["severity"] not in ALLOWED_SEVERITIES:
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "severity must be one of: %s" % ", ".join(ALLOWED_SEVERITIES)),
            )
        updates["severity"] = body["severity"]
    if "field_key" in body:
        updates["field_key"] = body["field_key"]
    if "issue_type" in body:
        updates["issue_type"] = body["issue_type"]
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
                "SELECT version, deleted_at, workspace_id FROM triage_items WHERE id = %s",
                (tri_id,),
            )
            row = cur.fetchone()
            if not row or row[1] is not None:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Triage item not found: %s" % tri_id),
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
            if "resolved_by" in updates:
                set_clauses.append("resolved_at = NOW()")
            set_clauses.append("version = version + 1")
            set_clauses.append("updated_at = NOW()")

            params.extend([tri_id, version])
            sql = "UPDATE triage_items SET %s WHERE id = %%s AND version = %%s RETURNING %s" % (
                ", ".join(set_clauses),
                TRIAGE_SELECT,
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
                event_type="triage_item.updated",
                actor_id=auth.user_id,
                resource_type="triage_item",
                resource_id=tri_id,
                detail={"fields": list(updates.keys()), "new_version": version + 1},
            )
        conn.commit()
        return envelope(_row_to_dict(updated, TRIAGE_COLUMNS))
    except Exception as e:
        logger.error("update_triage_item error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
