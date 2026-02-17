import logging
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.api_v25 import error_envelope
from server.auth import AuthClass, require_auth, require_role, get_workspace_role, Role
from server.role_scope import require_workspace_member

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")

PATCH_QUEUE_STATUS_MAP = {
    "Submitted": "pending",
    "Needs_Clarification": "needs_clarification",
    "Verifier_Responded": "pending",
    "Verifier_Approved": "sent_to_admin",
    "Admin_Hold": "sent_to_admin",
    "Admin_Approved": "resolved",
    "Applied": "resolved",
    "Rejected": "resolved",
    "Cancelled": "resolved",
    "Sent_to_Kiwi": "sent_to_admin",
    "Kiwi_Returned": "sent_to_admin",
}

RFI_QUEUE_STATUS_MAP = {
    "open": "pending",
    "awaiting_verifier": "pending",
    "returned_to_analyst": "needs_clarification",
    "resolved": "resolved",
    "dismissed": "resolved",
}

CORRECTION_QUEUE_STATUS_MAP = {
    "pending_verifier": "pending",
    "approved": "resolved",
    "rejected": "resolved",
    "auto_applied": "resolved",
}


def _iso(val):
    if isinstance(val, datetime):
        return val.isoformat()
    return val


def _resolve_effective_role(request, auth, ws_id):
    from server.role_scope import resolve_effective_role
    return resolve_effective_role(request, auth, ws_id)


def _build_patch_item(row):
    return {
        "id": row[0],
        "item_type": "patch",
        "workspace_id": row[1],
        "batch_id": row[2],
        "contract_id": None,
        "document_id": None,
        "record_id": row[3],
        "field_key": row[4],
        "lifecycle_status": row[5],
        "queue_status": PATCH_QUEUE_STATUS_MAP.get(row[5], "pending"),
        "custody_owner_id": None,
        "custody_owner_role": None,
        "author_id": row[6],
        "author_email": row[7],
        "decided_by": None,
        "summary": _patch_summary(row),
        "before_value": row[8],
        "after_value": row[9],
        "created_at": _iso(row[10]),
        "updated_at": _iso(row[11]),
        "resolved_at": _iso(row[12]),
        "version": row[13],
        "metadata": row[14] if row[14] else {},
    }


def _patch_summary(row):
    field_key = row[4] or ""
    after_value = row[9] or ""
    intent = row[15] or ""
    if intent:
        return intent[:120]
    if field_key and after_value:
        return "Set %s = '%s'" % (field_key, after_value[:60])
    return "Patch %s" % row[0][:12]


def _build_rfi_item(row):
    return {
        "id": row[0],
        "item_type": "rfi",
        "workspace_id": row[1],
        "batch_id": row[2],
        "contract_id": None,
        "document_id": None,
        "record_id": row[3],
        "field_key": row[4],
        "lifecycle_status": row[5] or "open",
        "queue_status": RFI_QUEUE_STATUS_MAP.get(row[6] or "open", "pending"),
        "custody_owner_id": row[7],
        "custody_owner_role": row[8],
        "author_id": row[9],
        "author_email": row[10],
        "decided_by": row[11],
        "summary": (row[12] or "")[:120],
        "before_value": None,
        "after_value": row[13],
        "created_at": _iso(row[14]),
        "updated_at": _iso(row[15]),
        "resolved_at": None,
        "version": row[16],
        "metadata": row[17] if row[17] else {},
    }


def _build_correction_item(row):
    return {
        "id": row[0],
        "item_type": "correction",
        "workspace_id": row[1],
        "batch_id": row[2],
        "contract_id": None,
        "document_id": row[3],
        "record_id": row[4],
        "field_key": row[5],
        "lifecycle_status": row[6],
        "queue_status": CORRECTION_QUEUE_STATUS_MAP.get(row[6], "pending"),
        "custody_owner_id": None,
        "custody_owner_role": None,
        "author_id": row[7],
        "author_email": row[8],
        "decided_by": row[9],
        "summary": _correction_summary(row),
        "before_value": row[10],
        "after_value": row[11],
        "created_at": _iso(row[12]),
        "updated_at": _iso(row[13]),
        "resolved_at": _iso(row[14]),
        "version": row[15],
        "metadata": row[16] if row[16] else {},
    }


def _correction_summary(row):
    field_key = row[5] or ""
    original = row[10] or ""
    corrected = row[11] or ""
    if field_key and corrected:
        return "Correct %s: '%s' → '%s'" % (field_key, original[:30], corrected[:30])
    return "Correction %s" % row[0][:12]


ANALYST_VISIBLE_PATCH_STATUSES = (
    "Submitted", "Needs_Clarification", "Verifier_Responded",
    "Verifier_Approved", "Admin_Approved", "Applied", "Rejected", "Cancelled",
)

VERIFIER_VISIBLE_PATCH_STATUSES = (
    "Submitted", "Needs_Clarification", "Verifier_Responded",
    "Verifier_Approved", "Admin_Hold", "Admin_Approved", "Applied", "Rejected",
)


@router.get("/workspaces/{ws_id}/operations/queue")
def operations_queue(
    ws_id: str,
    request: Request,
    queue_status: str = Query(None),
    batch_id: str = Query(None),
    item_type: str = Query(None),
    author_id: str = Query(None),
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    if auth.role and auth.user_id == 'sandbox_user':
        pass
    else:
        role_err = require_role(ws_id, auth, Role.ANALYST)
        if role_err is not None:
            return role_err

    effective_role = _resolve_effective_role(request, auth, ws_id)
    user_id = auth.user_id

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM workspaces WHERE id = %s AND deleted_at IS NULL", (ws_id,))
            if not cur.fetchone():
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Workspace not found: %s" % ws_id),
                )

            items = []

            if item_type is None or item_type == "patch":
                items.extend(_query_patches(cur, ws_id, batch_id, author_id, role=effective_role, user_id=user_id))

            if item_type is None or item_type == "rfi":
                items.extend(_query_rfis(cur, ws_id, batch_id, author_id, role=effective_role, user_id=user_id))

            if item_type is None or item_type == "correction":
                items.extend(_query_corrections(cur, ws_id, batch_id, author_id, role=effective_role, user_id=user_id))

            if queue_status:
                items = [i for i in items if i["queue_status"] == queue_status]

            counts = {"pending": 0, "needs_clarification": 0, "sent_to_admin": 0, "resolved": 0, "total": 0}
            all_items_for_counts = []
            if item_type is None or item_type == "patch":
                all_items_for_counts.extend(_query_patches(cur, ws_id, batch_id, None, role=effective_role, user_id=user_id))
            if item_type is None or item_type == "rfi":
                all_items_for_counts.extend(_query_rfis(cur, ws_id, batch_id, None, role=effective_role, user_id=user_id))
            if item_type is None or item_type == "correction":
                all_items_for_counts.extend(_query_corrections(cur, ws_id, batch_id, None, role=effective_role, user_id=user_id))
            for ci in all_items_for_counts:
                qs = ci["queue_status"]
                if qs in counts:
                    counts[qs] += 1
                counts["total"] += 1

            items.sort(key=lambda x: x.get("created_at") or "", reverse=True)

            if cursor:
                items = [i for i in items if i["id"] > cursor]

            has_more = len(items) > limit
            if has_more:
                items = items[:limit]

            next_cursor = items[-1]["id"] if items and has_more else None

        meta = {
            "cursor": next_cursor,
            "has_more": has_more,
            "limit": limit,
            "effective_role": effective_role,
        }
        return {
            "data": {
                "items": items,
                "counts": counts,
            },
            "meta": meta,
        }
    except Exception as e:
        logger.error("operations_queue error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


def _query_patches(cur, ws_id, batch_id, author_id, role="admin", user_id=None):
    conditions = ["p.workspace_id = %s", "p.deleted_at IS NULL", "p.status != 'Draft'"]
    params = [ws_id]

    if role == "analyst":
        if user_id:
            conditions.append("p.author_id = %s")
            params.append(user_id)
        if ANALYST_VISIBLE_PATCH_STATUSES:
            placeholders = ", ".join(["%s"] * len(ANALYST_VISIBLE_PATCH_STATUSES))
            conditions.append("p.status IN (%s)" % placeholders)
            params.extend(ANALYST_VISIBLE_PATCH_STATUSES)
    elif role == "verifier":
        if VERIFIER_VISIBLE_PATCH_STATUSES:
            placeholders = ", ".join(["%s"] * len(VERIFIER_VISIBLE_PATCH_STATUSES))
            conditions.append("p.status IN (%s)" % placeholders)
            params.extend(VERIFIER_VISIBLE_PATCH_STATUSES)

    if batch_id:
        conditions.append("p.batch_id = %s")
        params.append(batch_id)
    if author_id:
        conditions.append("p.author_id = %s")
        params.append(author_id)
    where = " AND ".join(conditions)
    cur.execute(
        """SELECT p.id, p.workspace_id, p.batch_id, p.record_id, p.field_key,
                  p.status, p.author_id, u.email,
                  p.before_value, p.after_value,
                  p.created_at, p.updated_at, p.resolved_at,
                  p.version, p.metadata, p.intent
           FROM patches p
           LEFT JOIN users u ON u.id = p.author_id
           WHERE %s
           ORDER BY p.created_at DESC""" % where,
        params,
    )
    return [_build_patch_item(row) for row in cur.fetchall()]


def _query_rfis(cur, ws_id, batch_id, author_id, role="admin", user_id=None):
    conditions = ["r.workspace_id = %s", "r.deleted_at IS NULL"]
    params = [ws_id]

    if role == "analyst" and user_id:
        conditions.append("r.author_id = %s")
        params.append(user_id)

    if batch_id:
        conditions.append("r.batch_id = %s")
        params.append(batch_id)
    if author_id:
        conditions.append("r.author_id = %s")
        params.append(author_id)
    where = " AND ".join(conditions)
    cur.execute(
        """SELECT r.id, r.workspace_id, r.batch_id, r.target_record_id, r.target_field_key,
                  r.status, r.custody_status, r.custody_owner_id, r.custody_owner_role,
                  r.author_id, u.email, r.responder_id,
                  r.question, r.response,
                  r.created_at, r.updated_at,
                  r.version, r.metadata
           FROM rfis r
           LEFT JOIN users u ON u.id = r.author_id
           WHERE %s
           ORDER BY r.created_at DESC""" % where,
        params,
    )
    return [_build_rfi_item(row) for row in cur.fetchall()]


def _query_corrections(cur, ws_id, batch_id, author_id, role="admin", user_id=None):
    conditions = ["c.workspace_id = %s", "c.deleted_at IS NULL"]
    params = [ws_id]

    if role == "analyst" and user_id:
        conditions.append("c.created_by = %s")
        params.append(user_id)

    if batch_id:
        conditions.append("d.batch_id = %s")
        params.append(batch_id)
    if author_id:
        conditions.append("c.created_by = %s")
        params.append(author_id)
    where = " AND ".join(conditions)
    cur.execute(
        """SELECT c.id, c.workspace_id, d.batch_id, c.document_id, c.field_id, c.field_key,
                  c.status, c.created_by, u.email, c.decided_by,
                  c.original_value, c.corrected_value,
                  c.created_at, c.updated_at, c.decided_at,
                  c.version, c.metadata
           FROM corrections c
           JOIN documents d ON d.id = c.document_id
           LEFT JOIN users u ON u.id = c.created_by
           WHERE %s
           ORDER BY c.created_at DESC""" % where,
        params,
    )
    return [_build_correction_item(row) for row in cur.fetchall()]


@router.get("/workspaces/{ws_id}/corrections")
def list_workspace_corrections(
    ws_id: str,
    request: Request,
    status: str = Query(None),
    batch_id: str = Query(None),
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
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

            from server.routes.corrections import CORRECTION_COLUMNS, CORRECTION_SELECT, _row_to_dict

            conditions = ["c.workspace_id = %s", "c.deleted_at IS NULL"]
            params = [ws_id]

            if effective_role == "analyst":
                conditions.append("c.created_by = %s")
                params.append(auth.user_id)

            if status:
                conditions.append("c.status = %s")
                params.append(status)
            if batch_id:
                conditions.append("c.document_id IN (SELECT id FROM documents WHERE batch_id = %s AND deleted_at IS NULL)")
                params.append(batch_id)
            if cursor:
                conditions.append("c.id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            col_list = ", ".join(["c." + col for col in CORRECTION_COLUMNS])
            sql = "SELECT %s FROM corrections c %s ORDER BY c.id ASC LIMIT %%s" % (col_list, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, CORRECTION_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        from server.api_v25 import collection_envelope
        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_workspace_corrections error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
