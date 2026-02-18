import json
import logging
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.ulid import generate_id
from server.api_v25 import envelope, collection_envelope, error_envelope
from server.auth import AuthClass, require_auth, get_workspace_role
from server.audit import emit_audit_event
from server.feature_flags import require_evidence_inspector

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")

CORRECTION_COLUMNS = [
    "id", "document_id", "workspace_id", "anchor_id", "rfi_id",
    "field_id", "field_key", "original_value", "corrected_value",
    "correction_type", "status", "decided_by", "decided_at",
    "created_by", "created_at", "updated_at", "deleted_at", "version", "metadata",
]
CORRECTION_SELECT = ", ".join(CORRECTION_COLUMNS)

ALLOWED_STATUSES = ("pending_verifier", "approved", "rejected", "auto_applied")
ALLOWED_CORRECTION_TYPES = ("minor", "non_trivial")

STATUS_TRANSITIONS = {
    "pending_verifier": {"approved", "rejected"},
    "auto_applied": set(),
    "approved": set(),
    "rejected": set(),
}


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


def _classify_correction(original_value, corrected_value):
    if original_value is None or corrected_value is None:
        return "non_trivial"
    length_delta = abs(len(corrected_value) - len(original_value))
    if length_delta > 2:
        return "non_trivial"
    if re.search(r'\d', corrected_value) and not re.search(r'\d', original_value):
        return "non_trivial"
    if re.search(r'\d', original_value) and not re.search(r'\d', corrected_value):
        return "non_trivial"
    currency_pct = re.compile(r'[$€£¥%]')
    if currency_pct.search(corrected_value) or currency_pct.search(original_value):
        return "non_trivial"
    return "minor"


@router.post("/documents/{doc_id}/corrections", status_code=201)
def create_correction(
    doc_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth
    gate = require_evidence_inspector()
    if gate:
        return gate

    original_value = body.get("original_value")
    corrected_value = body.get("corrected_value")
    if corrected_value is None:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "corrected_value is required"),
        )

    anchor_id = body.get("anchor_id")
    rfi_id = body.get("rfi_id")
    field_id = body.get("field_id")
    field_key = body.get("field_key")
    metadata = body.get("metadata", {})

    correction_type = _classify_correction(original_value, corrected_value)
    if correction_type == "minor":
        status = "auto_applied"
    else:
        status = "pending_verifier"

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

            if anchor_id:
                cur.execute("SELECT id FROM anchors WHERE id = %s AND deleted_at IS NULL", (anchor_id,))
                if not cur.fetchone():
                    return JSONResponse(
                        status_code=400,
                        content=error_envelope("VALIDATION_ERROR", "anchor_id not found: %s" % anchor_id),
                    )

            if rfi_id:
                cur.execute("SELECT id FROM rfis WHERE id = %s AND deleted_at IS NULL", (rfi_id,))
                if not cur.fetchone():
                    return JSONResponse(
                        status_code=400,
                        content=error_envelope("VALIDATION_ERROR", "rfi_id not found: %s" % rfi_id),
                    )

            cor_id = generate_id("cor_")
            cur.execute(
                """INSERT INTO corrections
                   (id, document_id, workspace_id, anchor_id, rfi_id,
                    field_id, field_key, original_value, corrected_value,
                    correction_type, status, created_by, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + CORRECTION_SELECT,
                (cor_id, doc_id, workspace_id, anchor_id, rfi_id,
                 field_id, field_key, original_value, corrected_value,
                 correction_type, status, auth.user_id, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="correction.created",
                actor_id=auth.user_id,
                resource_type="correction",
                resource_id=cor_id,
                detail={
                    "document_id": doc_id,
                    "correction_type": correction_type,
                    "status": status,
                    "field_id": field_id,
                },
            )

            if correction_type == "minor":
                emit_audit_event(
                    cur,
                    workspace_id=workspace_id,
                    event_type="CORRECTION_APPLIED_MINOR",
                    actor_id=auth.user_id,
                    resource_type="correction",
                    resource_id=cor_id,
                    detail={
                        "document_id": doc_id,
                        "original_value": original_value,
                        "corrected_value": corrected_value,
                        "field_key": field_key,
                    },
                )
            else:
                emit_audit_event(
                    cur,
                    workspace_id=workspace_id,
                    event_type="CORRECTION_PROPOSED",
                    actor_id=auth.user_id,
                    resource_type="correction",
                    resource_id=cor_id,
                    detail={
                        "document_id": doc_id,
                        "original_value": original_value,
                        "corrected_value": corrected_value,
                        "field_key": field_key,
                        "correction_type": correction_type,
                    },
                )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, CORRECTION_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_correction error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/corrections/{cor_id}")
def update_correction(
    cor_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth
    gate = require_evidence_inspector()
    if gate:
        return gate

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
    if "corrected_value" in body:
        updates["corrected_value"] = body["corrected_value"]
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
                "SELECT version, deleted_at, workspace_id, status FROM corrections WHERE id = %s",
                (cor_id,),
            )
            row = cur.fetchone()
            if not row or row[1] is not None:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Correction not found: %s" % cor_id),
                )

            current_version = row[0]
            workspace_id = row[2]
            old_status = row[3]
            if current_version != version:
                return JSONResponse(
                    status_code=409,
                    content=error_envelope(
                        "STALE_VERSION",
                        "Resource has been modified since your last read",
                        details={"current_version": current_version, "provided_version": version},
                    ),
                )

            if "status" in updates:
                new_status = updates["status"]
                allowed_next = STATUS_TRANSITIONS.get(old_status, set())
                if new_status != old_status and new_status not in allowed_next:
                    return JSONResponse(
                        status_code=409,
                        content=error_envelope(
                            "INVALID_TRANSITION",
                            "Cannot transition correction status from '%s' to '%s'. Allowed: %s"
                            % (old_status, new_status, ", ".join(sorted(allowed_next)) if allowed_next else "none (terminal)"),
                        ),
                    )

                if new_status in ("approved", "rejected") and new_status != old_status:
                    actor_role = get_workspace_role(auth.user_id, workspace_id)
                    if actor_role is None and auth.user_id == "sandbox_user":
                        actor_role = getattr(auth, 'role', None)
                    verifier_roles = {"verifier", "admin", "architect"}
                    if actor_role not in verifier_roles:
                        return JSONResponse(
                            status_code=403,
                            content=error_envelope(
                                "ROLE_NOT_ALLOWED",
                                "Only verifier, admin, or architect roles can approve or reject corrections",
                                details={"required_roles": sorted(verifier_roles), "your_role": actor_role},
                            ),
                        )

            if "status" in updates and updates["status"] in ("approved", "rejected"):
                updates["decided_by"] = auth.user_id
                updates["decided_at"] = datetime.now(timezone.utc)

            set_clauses = []
            params: list = []
            for k, v in updates.items():
                if k == "metadata":
                    set_clauses.append("metadata = %s::jsonb")
                    params.append(json.dumps(v))
                elif k == "decided_at":
                    set_clauses.append("decided_at = %s")
                    params.append(v)
                else:
                    set_clauses.append("%s = %%s" % k)
                    params.append(v)
            set_clauses.append("version = version + 1")
            set_clauses.append("updated_at = NOW()")

            params.extend([cor_id, version])
            sql = "UPDATE corrections SET %s WHERE id = %%s AND version = %%s RETURNING %s" % (
                ", ".join(set_clauses),
                CORRECTION_SELECT,
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
                event_type="correction.updated",
                actor_id=auth.user_id,
                resource_type="correction",
                resource_id=cor_id,
                detail={
                    "fields": list(updates.keys()),
                    "old_status": old_status,
                    "new_status": updates.get("status", old_status),
                    "new_version": version + 1,
                },
            )

            if "status" in updates:
                new_status = updates["status"]
                if new_status == "approved" and old_status != "approved":
                    emit_audit_event(
                        cur,
                        workspace_id=workspace_id,
                        event_type="CORRECTION_APPROVED",
                        actor_id=auth.user_id,
                        resource_type="correction",
                        resource_id=cor_id,
                        detail={"decided_by": auth.user_id},
                    )
                elif new_status == "rejected" and old_status != "rejected":
                    emit_audit_event(
                        cur,
                        workspace_id=workspace_id,
                        event_type="CORRECTION_REJECTED",
                        actor_id=auth.user_id,
                        resource_type="correction",
                        resource_id=cor_id,
                        detail={"decided_by": auth.user_id},
                    )
        conn.commit()
        return envelope(_row_to_dict(updated, CORRECTION_COLUMNS))
    except Exception as e:
        logger.error("update_correction error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/batches/{bat_id}/corrections")
def list_batch_corrections(
    bat_id: str,
    status: str = Query(None),
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
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
            cur.execute("SELECT id FROM batches WHERE id = %s AND deleted_at IS NULL", (bat_id,))
            if not cur.fetchone():
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Batch not found: %s" % bat_id),
                )

            conditions = [
                "c.document_id IN (SELECT id FROM documents WHERE batch_id = %s AND deleted_at IS NULL)"
            ]
            params: list = [bat_id]

            conditions.append("c.deleted_at IS NULL")
            if status:
                conditions.append("c.status = %s")
                params.append(status)
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

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_batch_corrections error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
