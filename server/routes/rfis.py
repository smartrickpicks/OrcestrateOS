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

ALLOWED_STATUSES = ("open", "responded", "closed")
CUSTODY_STATUSES = ("open", "awaiting_verifier", "returned_to_analyst", "resolved", "dismissed")

CUSTODY_TRANSITIONS = {
    "open": {"awaiting_verifier"},
    "awaiting_verifier": {"returned_to_analyst", "resolved", "dismissed"},
    "returned_to_analyst": {"awaiting_verifier"},
    "resolved": set(),
    "dismissed": set(),
}

CUSTODY_OWNER_MAP = {
    "open": "analyst",
    "awaiting_verifier": "verifier",
    "returned_to_analyst": "analyst",
    "resolved": None,
    "dismissed": None,
}

CUSTODY_AUDIT_EVENT_MAP = {
    ("open", "awaiting_verifier"): "RFI_SENT",
    ("awaiting_verifier", "returned_to_analyst"): "RFI_RETURNED",
    ("awaiting_verifier", "resolved"): "RFI_RESOLVED",
    ("awaiting_verifier", "dismissed"): "RFI_RESOLVED",
    ("returned_to_analyst", "awaiting_verifier"): "RFI_SENT",
}

RFI_COLUMNS = [
    "id", "workspace_id", "patch_id", "author_id", "target_record_id",
    "target_field_key", "question", "response", "responder_id", "status",
    "created_at", "updated_at", "deleted_at", "version", "metadata",
    "custody_status", "custody_owner_id", "custody_owner_role",
]
RFI_SELECT = ", ".join(RFI_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/workspaces/{ws_id}/rfis")
def list_rfis(
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
            params: list = [ws_id]

            if not include_deleted:
                conditions.append("deleted_at IS NULL")
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM rfis %s ORDER BY id ASC LIMIT %%s" % (RFI_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, RFI_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_rfis error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/workspaces/{ws_id}/rfis", status_code=201)
def create_rfi(
    ws_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    question = body.get("question")
    if not question or not isinstance(question, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "question is required and must be a string"),
        )

    target_record_id = body.get("target_record_id")
    if not target_record_id or not isinstance(target_record_id, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "target_record_id is required and must be a string"),
        )

    patch_id = body.get("patch_id")
    target_field_key = body.get("target_field_key")
    status = body.get("status", "open")
    if status not in ALLOWED_STATUSES:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "status must be one of: %s" % ", ".join(ALLOWED_STATUSES)),
        )
    metadata = body.get("metadata", {})
    if patch_id:
        metadata["frontend_patch_id"] = patch_id
    rfi_id = generate_id("rfi_")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM workspaces WHERE id = %s AND deleted_at IS NULL", (ws_id,))
            if not cur.fetchone():
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Workspace not found: %s" % ws_id),
                )

            db_patch_id = None
            if patch_id:
                cur.execute("SELECT id FROM patches WHERE id = %s AND deleted_at IS NULL", (patch_id,))
                if cur.fetchone():
                    db_patch_id = patch_id

            cur.execute(
                """INSERT INTO rfis
                   (id, workspace_id, patch_id, author_id, target_record_id,
                    target_field_key, question, status, metadata,
                    custody_status, custody_owner_id, custody_owner_role)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + RFI_SELECT,
                (rfi_id, ws_id, db_patch_id, auth.user_id, target_record_id,
                 target_field_key, question, status, json.dumps(metadata),
                 "open", auth.user_id, "analyst"),
            )
            row = cur.fetchone()

            audit_detail = {"question": question, "target_record_id": target_record_id}
            if auth.is_role_simulated:
                audit_detail["simulated_role"] = True
                audit_detail["actual_role"] = auth.actual_role
                audit_detail["effective_role"] = auth.effective_role
            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="rfi.created",
                actor_id=auth.user_id,
                resource_type="rfi",
                resource_id=rfi_id,
                detail=audit_detail,
            )
            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="RFI_CREATED",
                actor_id=auth.user_id,
                resource_type="rfi",
                resource_id=rfi_id,
                detail={"custody_status": "open", "custody_owner_role": "analyst"},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, RFI_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_rfi error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/rfis/{rfi_id}")
def get_rfi(
    rfi_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM rfis WHERE id = %%s AND deleted_at IS NULL" % RFI_SELECT,
                (rfi_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "RFI not found: %s" % rfi_id),
            )
        return envelope(_row_to_dict(row, RFI_COLUMNS))
    except Exception as e:
        logger.error("get_rfi error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/rfis/{rfi_id}")
def update_rfi(
    rfi_id: str,
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
    if "question" in body:
        updates["question"] = body["question"]
    if "response" in body:
        updates["response"] = body["response"]
        updates["responder_id"] = auth.user_id
        updates["status"] = "responded"
    if "target_field_key" in body:
        updates["target_field_key"] = body["target_field_key"]
    if "status" in body and "response" not in body:
        if body["status"] not in ALLOWED_STATUSES:
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "status must be one of: %s" % ", ".join(ALLOWED_STATUSES)),
            )
        updates["status"] = body["status"]
    if "patch_id" in body:
        updates["patch_id"] = body["patch_id"]
    if "metadata" in body:
        updates["metadata"] = body["metadata"]

    custody_transition_requested = "custody_status" in body
    requested_custody = body.get("custody_status")

    if custody_transition_requested:
        if requested_custody not in CUSTODY_STATUSES:
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "custody_status must be one of: %s" % ", ".join(CUSTODY_STATUSES)),
            )

    if not updates and not custody_transition_requested:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "No updatable fields provided"),
        )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT version, deleted_at, workspace_id, status, custody_status, custody_owner_id, custody_owner_role FROM rfis WHERE id = %s",
                (rfi_id,),
            )
            row = cur.fetchone()
            if not row or row[1] is not None:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "RFI not found: %s" % rfi_id),
                )

            current_version = row[0]
            workspace_id = row[2]
            old_status = row[3]
            old_custody = row[4] or "open"
            old_custody_owner_id = row[5]
            old_custody_owner_role = row[6]

            if current_version != version:
                return JSONResponse(
                    status_code=409,
                    content=error_envelope(
                        "STALE_VERSION",
                        "Resource has been modified since your last read",
                        details={"current_version": current_version, "provided_version": version},
                    ),
                )

            if custody_transition_requested:
                if requested_custody == old_custody:
                    pass
                else:
                    allowed = CUSTODY_TRANSITIONS.get(old_custody, set())
                    if requested_custody not in allowed:
                        return JSONResponse(
                            status_code=400,
                            content=error_envelope(
                                "INVALID_TRANSITION",
                                "Cannot transition custody_status from '%s' to '%s'. Allowed: %s"
                                % (old_custody, requested_custody, ", ".join(sorted(allowed)) if allowed else "none (terminal)"),
                            ),
                        )

                updates["custody_status"] = requested_custody
                new_owner_role = CUSTODY_OWNER_MAP.get(requested_custody)
                updates["custody_owner_role"] = new_owner_role
                if new_owner_role == "analyst":
                    if old_custody_owner_role == "analyst" and old_custody_owner_id:
                        updates["custody_owner_id"] = old_custody_owner_id
                    else:
                        cur.execute("SELECT author_id FROM rfis WHERE id = %s", (rfi_id,))
                        updates["custody_owner_id"] = cur.fetchone()[0]
                elif new_owner_role == "verifier":
                    updates["custody_owner_id"] = auth.user_id
                else:
                    updates["custody_owner_id"] = None

            set_clauses = []
            params: list = []
            for k, v in updates.items():
                if k == "metadata":
                    set_clauses.append("metadata = %s::jsonb")
                    params.append(json.dumps(v))
                else:
                    set_clauses.append("%s = %%s" % k)
                    params.append(v)
            set_clauses.append("version = version + 1")
            set_clauses.append("updated_at = NOW()")

            params.extend([rfi_id, version])
            sql = "UPDATE rfis SET %s WHERE id = %%s AND version = %%s RETURNING %s" % (
                ", ".join(set_clauses),
                RFI_SELECT,
            )
            cur.execute(sql, params)
            updated = cur.fetchone()

            if not updated:
                conn.rollback()
                return JSONResponse(
                    status_code=409,
                    content=error_envelope("STALE_VERSION", "Concurrent modification detected"),
                )

            audit_detail = {"fields": list(updates.keys()), "new_version": version + 1}
            if "custody_status" in updates:
                audit_detail["old_custody_status"] = old_custody
                audit_detail["custody_status"] = updates["custody_status"]
                audit_detail["custody_owner_role"] = updates.get("custody_owner_role")
            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="rfi.updated",
                actor_id=auth.user_id,
                resource_type="rfi",
                resource_id=rfi_id,
                detail=audit_detail,
            )

            if custody_transition_requested and requested_custody != old_custody:
                custody_event = CUSTODY_AUDIT_EVENT_MAP.get((old_custody, requested_custody))
                if custody_event:
                    emit_audit_event(
                        cur,
                        workspace_id=workspace_id,
                        event_type=custody_event,
                        actor_id=auth.user_id,
                        resource_type="rfi",
                        resource_id=rfi_id,
                        detail={
                            "from_custody_status": old_custody,
                            "to_custody_status": requested_custody,
                            "custody_owner_role": updates.get("custody_owner_role"),
                            "custody_owner_id": updates.get("custody_owner_id"),
                        },
                    )
        conn.commit()
        return envelope(_row_to_dict(updated, RFI_COLUMNS))
    except Exception as e:
        logger.error("update_rfi error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/batches/{bat_id}/rfis")
def list_batch_rfis(
    bat_id: str,
    status: str = Query(None),
    custody_status: str = Query(None),
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    from server.feature_flags import require_evidence_inspector
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

            conditions = ["workspace_id = %s", "deleted_at IS NULL"]
            params: list = [workspace_id]

            if custody_status:
                conditions.append("custody_status = %s")
                params.append(custody_status)
            elif status:
                conditions.append("(custody_status = %s OR (custody_status IS NULL AND status = %s))")
                params.extend([status, status])
            else:
                conditions.append("(custody_status IN ('open', 'awaiting_verifier') OR (custody_status IS NULL AND status IN ('open', 'responded')))")

            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM rfis %s ORDER BY id ASC LIMIT %%s" % (RFI_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, RFI_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_batch_rfis error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
