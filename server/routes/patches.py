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
from server.role_scope import require_workspace_member

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")

VISIBLE_STATUSES = (
    "Draft", "Submitted", "Needs_Clarification", "Verifier_Responded",
    "Verifier_Approved", "Admin_Approved", "Admin_Hold",
    "Applied", "Rejected", "Cancelled",
)
HIDDEN_STATUSES = ("Sent_to_Kiwi", "Kiwi_Returned")
ALL_STATUSES = VISIBLE_STATUSES + HIDDEN_STATUSES
TERMINAL_STATUSES = ("Applied", "Rejected", "Cancelled")

TRANSITION_MATRIX = {
    ("Draft", "Submitted"): {"min_role": "analyst", "author_only": True, "self_approval_check": False},
    ("Draft", "Cancelled"): {"min_role": "analyst", "author_only": True, "self_approval_check": False},
    ("Submitted", "Needs_Clarification"): {"min_role": "verifier", "author_only": False, "self_approval_check": False},
    ("Submitted", "Verifier_Approved"): {"min_role": "verifier", "author_only": False, "self_approval_check": True},
    ("Submitted", "Rejected"): {"min_role": "verifier", "author_only": False, "self_approval_check": False},
    ("Submitted", "Cancelled"): {"min_role": "analyst", "author_only": True, "self_approval_check": False},
    ("Needs_Clarification", "Verifier_Responded"): {"min_role": "analyst", "author_only": True, "self_approval_check": False},
    ("Needs_Clarification", "Cancelled"): {"min_role": "analyst", "author_only": True, "self_approval_check": False},
    ("Verifier_Responded", "Verifier_Approved"): {"min_role": "verifier", "author_only": False, "self_approval_check": True},
    ("Verifier_Responded", "Needs_Clarification"): {"min_role": "verifier", "author_only": False, "self_approval_check": False},
    ("Verifier_Responded", "Rejected"): {"min_role": "verifier", "author_only": False, "self_approval_check": False},
    ("Verifier_Responded", "Cancelled"): {"min_role": "analyst", "author_only": True, "self_approval_check": False},
    ("Verifier_Approved", "Admin_Approved"): {"min_role": "admin", "author_only": False, "self_approval_check": True},
    ("Verifier_Approved", "Admin_Hold"): {"min_role": "admin", "author_only": False, "self_approval_check": False},
    ("Verifier_Approved", "Cancelled"): {"min_role": "analyst", "author_only": True, "self_approval_check": False},
    ("Admin_Hold", "Admin_Approved"): {"min_role": "admin", "author_only": False, "self_approval_check": True},
    ("Admin_Hold", "Rejected"): {"min_role": "admin", "author_only": False, "self_approval_check": False},
    ("Admin_Approved", "Applied"): {"min_role": "admin", "author_only": False, "self_approval_check": False},
    ("Admin_Approved", "Sent_to_Kiwi"): {"min_role": "admin", "author_only": False, "self_approval_check": False},
    ("Sent_to_Kiwi", "Kiwi_Returned"): {"min_role": "admin", "author_only": False, "self_approval_check": False},
    ("Kiwi_Returned", "Admin_Approved"): {"min_role": "admin", "author_only": False, "self_approval_check": False},
    ("Kiwi_Returned", "Rejected"): {"min_role": "admin", "author_only": False, "self_approval_check": False},
}

ROLE_HIERARCHY = {"analyst": 0, "verifier": 1, "admin": 2, "architect": 3}

PATCH_COLUMNS = [
    "id", "workspace_id", "batch_id", "record_id", "field_key",
    "author_id", "status", "intent", "when_clause", "then_clause",
    "because_clause", "evidence_pack_id", "submitted_at", "resolved_at",
    "file_name", "file_url", "before_value", "after_value",
    "history", "created_at", "updated_at", "deleted_at", "version", "metadata",
]
PATCH_SELECT = ", ".join(PATCH_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


def _check_role(user_id, workspace_id, min_role, conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT role FROM user_workspace_roles WHERE user_id = %s AND workspace_id = %s",
            (user_id, workspace_id),
        )
        row = cur.fetchone()
    if not row:
        return None, "No role assigned in this workspace"
    user_role = row[0]
    if ROLE_HIERARCHY.get(user_role, -1) < ROLE_HIERARCHY.get(min_role, -1):
        return None, "Insufficient role: requires %s, you have %s" % (min_role, user_role)
    return user_role, None


@router.get("/workspaces/{ws_id}/patches")
def list_patches(
    ws_id: str,
    request: Request = None,
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    status: str = Query(None),
    author_id: str = Query(None),
    record_id: str = Query(None),
    batch_id: str = Query(None),
    include_hidden: bool = Query(False),
    include_deleted: bool = Query(False),
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    effective_role, role_err = require_workspace_member(request, auth, ws_id)
    if role_err is not None:
        return role_err

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

            if effective_role == "analyst":
                conditions.append("author_id = %s")
                params.append(auth.user_id)

            if not include_deleted:
                conditions.append("deleted_at IS NULL")
            if not include_hidden:
                conditions.append("status NOT IN ('Sent_to_Kiwi', 'Kiwi_Returned')")
            if status:
                if status not in ALL_STATUSES:
                    return JSONResponse(
                        status_code=400,
                        content=error_envelope("VALIDATION_ERROR", "Invalid status filter: %s" % status),
                    )
                conditions.append("status = %s")
                params.append(status)
            if author_id:
                conditions.append("author_id = %s")
                params.append(author_id)
            if record_id:
                conditions.append("record_id = %s")
                params.append(record_id)
            if batch_id:
                conditions.append("batch_id = %s")
                params.append(batch_id)
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM patches %s ORDER BY id ASC LIMIT %%s" % (PATCH_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, PATCH_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_patches error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/workspaces/{ws_id}/patches", status_code=201)
def create_patch(
    ws_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    batch_id = body.get("batch_id")
    record_id = body.get("record_id")
    field_key = body.get("field_key")
    intent = body.get("intent")
    when_clause = body.get("when_clause")
    then_clause = body.get("then_clause")
    because_clause = body.get("because_clause")
    before_value = body.get("before_value")
    after_value = body.get("after_value")
    metadata = body.get("metadata", {})

    pat_id = generate_id("pat_")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM workspaces WHERE id = %s AND deleted_at IS NULL", (ws_id,))
            if not cur.fetchone():
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Workspace not found: %s" % ws_id),
                )

            if batch_id:
                cur.execute("SELECT id FROM batches WHERE id = %s AND workspace_id = %s AND deleted_at IS NULL", (batch_id, ws_id))
                if not cur.fetchone():
                    return JSONResponse(
                        status_code=404,
                        content=error_envelope("NOT_FOUND", "Batch not found: %s" % batch_id),
                    )

            cur.execute(
                """INSERT INTO patches
                   (id, workspace_id, batch_id, record_id, field_key,
                    author_id, status, intent, when_clause, then_clause,
                    because_clause, before_value, after_value, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, 'Draft', %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + PATCH_SELECT,
                (pat_id, ws_id, batch_id, record_id, field_key,
                 auth.user_id, intent,
                 json.dumps(when_clause) if when_clause else None,
                 json.dumps(then_clause) if then_clause else None,
                 because_clause, before_value, after_value,
                 json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="patch.created",
                actor_id=auth.user_id,
                resource_type="patch",
                resource_id=pat_id,
                batch_id=batch_id,
                patch_id=pat_id,
                detail={"intent": intent, "status": "Draft"},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, PATCH_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_patch error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/patches/{pat_id}")
def get_patch(
    pat_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM patches WHERE id = %%s AND deleted_at IS NULL" % PATCH_SELECT,
                (pat_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Patch not found: %s" % pat_id),
            )
        return envelope(_row_to_dict(row, PATCH_COLUMNS))
    except Exception as e:
        logger.error("get_patch error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/patches/{pat_id}")
def update_patch(
    pat_id: str,
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

    new_status = body.get("status")
    user_role = None

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM patches WHERE id = %%s" % PATCH_SELECT,
                (pat_id,),
            )
            row = cur.fetchone()
            if not row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Patch not found: %s" % pat_id),
                )

            current = _row_to_dict(row, PATCH_COLUMNS)
            if current["deleted_at"] is not None:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Patch not found: %s" % pat_id),
                )

            current_version = current["version"]
            if current_version != version:
                return JSONResponse(
                    status_code=409,
                    content=error_envelope(
                        "STALE_VERSION",
                        "Resource has been modified since your last read",
                        details={"current_version": current_version, "provided_version": version},
                    ),
                )

            workspace_id = current["workspace_id"]
            current_status = current["status"]
            author_id = current["author_id"]

            if new_status and new_status != current_status:
                if new_status not in ALL_STATUSES:
                    return JSONResponse(
                        status_code=400,
                        content=error_envelope("VALIDATION_ERROR", "Invalid status: %s" % new_status),
                    )

                transition_key = (current_status, new_status)
                rule = TRANSITION_MATRIX.get(transition_key)
                if not rule:
                    return JSONResponse(
                        status_code=409,
                        content=error_envelope(
                            "INVALID_TRANSITION",
                            "Status transition from %s to %s is not allowed" % (current_status, new_status),
                            details={"from_status": current_status, "to_status": new_status},
                        ),
                    )

                if rule["author_only"] and auth.user_id != author_id:
                    return JSONResponse(
                        status_code=403,
                        content=error_envelope(
                            "FORBIDDEN",
                            "Only the patch author can perform this transition",
                        ),
                    )

                if not rule["author_only"]:
                    user_role, err_msg = _check_role(auth.user_id, workspace_id, rule["min_role"], conn)
                    if err_msg:
                        return JSONResponse(
                            status_code=403,
                            content=error_envelope("FORBIDDEN", err_msg),
                        )
                else:
                    user_role, _ = _check_role(auth.user_id, workspace_id, "analyst", conn)

                if rule["self_approval_check"] and auth.user_id == author_id:
                    emit_audit_event(
                        cur,
                        workspace_id=workspace_id,
                        event_type="patch.self_approval_blocked",
                        actor_id=auth.user_id,
                        resource_type="patch",
                        resource_id=pat_id,
                        patch_id=pat_id,
                        detail={"attempted_transition": new_status, "from_status": current_status},
                    )
                    conn.commit()
                    return JSONResponse(
                        status_code=403,
                        content=error_envelope(
                            "SELF_APPROVAL_BLOCKED",
                            "Cannot approve your own patch",
                            details={"patch_id": pat_id, "author_id": author_id},
                        ),
                    )

            set_clauses = []
            params = []

            if new_status and new_status != current_status:
                set_clauses.append("status = %s")
                params.append(new_status)

                if new_status == "Submitted" and current_status == "Draft":
                    set_clauses.append("submitted_at = NOW()")
                if new_status in TERMINAL_STATUSES:
                    set_clauses.append("resolved_at = NOW()")

                history_entry = json.dumps({
                    "from": current_status,
                    "to": new_status,
                    "actor_id": auth.user_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                })
                set_clauses.append("history = history || %s::jsonb")
                params.append("[%s]" % history_entry)

            field_updates = {}
            for field in ("intent", "because_clause", "before_value", "after_value",
                          "file_name", "file_url", "record_id", "field_key"):
                if field in body:
                    set_clauses.append("%s = %%s" % field)
                    params.append(body[field])
                    field_updates[field] = body[field]

            if "when_clause" in body:
                set_clauses.append("when_clause = %s::jsonb")
                params.append(json.dumps(body["when_clause"]))
                field_updates["when_clause"] = body["when_clause"]
            if "then_clause" in body:
                set_clauses.append("then_clause = %s::jsonb")
                params.append(json.dumps(body["then_clause"]))
                field_updates["then_clause"] = body["then_clause"]
            if "metadata" in body:
                set_clauses.append("metadata = %s::jsonb")
                params.append(json.dumps(body["metadata"]))
                field_updates["metadata"] = body["metadata"]

            if not set_clauses:
                return JSONResponse(
                    status_code=400,
                    content=error_envelope("VALIDATION_ERROR", "No updatable fields provided"),
                )

            set_clauses.append("version = version + 1")
            set_clauses.append("updated_at = NOW()")

            params.extend([pat_id, version])
            sql = "UPDATE patches SET %s WHERE id = %%s AND version = %%s RETURNING %s" % (
                ", ".join(set_clauses),
                PATCH_SELECT,
            )
            cur.execute(sql, params)
            updated = cur.fetchone()

            if not updated:
                conn.rollback()
                return JSONResponse(
                    status_code=409,
                    content=error_envelope("STALE_VERSION", "Concurrent modification detected"),
                )

            event_type = "patch.updated"
            detail = {"fields": list(field_updates.keys()), "new_version": version + 1}
            if new_status and new_status != current_status:
                event_type = "patch.status_changed"
                detail = {
                    "from_status": current_status,
                    "to_status": new_status,
                    "new_version": version + 1,
                }

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type=event_type,
                actor_id=auth.user_id,
                actor_role=user_role,
                resource_type="patch",
                resource_id=pat_id,
                patch_id=pat_id,
                detail=detail,
            )
        conn.commit()
        return envelope(_row_to_dict(updated, PATCH_COLUMNS))
    except Exception as e:
        logger.error("update_patch error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
