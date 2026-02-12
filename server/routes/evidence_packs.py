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

ALLOWED_STATUSES = ("incomplete", "complete")

EVP_COLUMNS = [
    "id", "patch_id", "workspace_id", "author_id", "blocks",
    "status", "created_at", "updated_at", "deleted_at", "version", "metadata",
]
EVP_SELECT = ", ".join(EVP_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/patches/{pat_id}/evidence-packs")
def list_evidence_packs(
    pat_id: str,
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
                "SELECT id, workspace_id FROM patches WHERE id = %s AND deleted_at IS NULL",
                (pat_id,),
            )
            patch_row = cur.fetchone()
            if not patch_row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Patch not found: %s" % pat_id),
                )

            conditions = ["patch_id = %s"]
            params = [pat_id]

            if not include_deleted:
                conditions.append("deleted_at IS NULL")
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM evidence_packs %s ORDER BY id ASC LIMIT %%s" % (EVP_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, EVP_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_evidence_packs error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/patches/{pat_id}/evidence-packs", status_code=201)
def create_evidence_pack(
    pat_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    blocks = body.get("blocks")
    if blocks is None or not isinstance(blocks, list):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "blocks is required and must be a JSON array"),
        )

    status = body.get("status", "incomplete")
    metadata = body.get("metadata", {})
    evp_id = generate_id("evp_")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, workspace_id FROM patches WHERE id = %s AND deleted_at IS NULL",
                (pat_id,),
            )
            patch_row = cur.fetchone()
            if not patch_row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Patch not found: %s" % pat_id),
                )
            workspace_id = patch_row[1]

            cur.execute(
                """INSERT INTO evidence_packs
                   (id, patch_id, workspace_id, author_id, blocks, status, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + EVP_SELECT,
                (evp_id, pat_id, workspace_id, auth.user_id,
                 json.dumps(blocks), status, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="evidence_pack.created",
                actor_id=auth.user_id,
                resource_type="evidence_pack",
                resource_id=evp_id,
                patch_id=pat_id,
                detail={"status": status, "block_count": len(blocks)},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, EVP_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_evidence_pack error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/evidence-packs/{evp_id}")
def get_evidence_pack(
    evp_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM evidence_packs WHERE id = %%s AND deleted_at IS NULL" % EVP_SELECT,
                (evp_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Evidence pack not found: %s" % evp_id),
            )
        return envelope(_row_to_dict(row, EVP_COLUMNS))
    except Exception as e:
        logger.error("get_evidence_pack error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/evidence-packs/{evp_id}")
def update_evidence_pack(
    evp_id: str,
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
    if "blocks" in body:
        if not isinstance(body["blocks"], list):
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "blocks must be a JSON array"),
            )
        updates["blocks"] = body["blocks"]
    if "status" in body:
        updates["status"] = body["status"]
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
                "SELECT version, deleted_at, workspace_id FROM evidence_packs WHERE id = %s",
                (evp_id,),
            )
            row = cur.fetchone()
            if not row or row[1] is not None:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Evidence pack not found: %s" % evp_id),
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
                if k in ("metadata", "blocks"):
                    set_clauses.append("%s = %%s::jsonb" % k)
                    params.append(json.dumps(v))
                else:
                    set_clauses.append("%s = %%s" % k)
                    params.append(v)
            set_clauses.append("version = version + 1")
            set_clauses.append("updated_at = NOW()")

            params.extend([evp_id, version])
            sql = "UPDATE evidence_packs SET %s WHERE id = %%s AND version = %%s RETURNING %s" % (
                ", ".join(set_clauses),
                EVP_SELECT,
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
                event_type="evidence_pack.updated",
                actor_id=auth.user_id,
                resource_type="evidence_pack",
                resource_id=evp_id,
                detail={"fields": list(updates.keys()), "new_version": version + 1},
            )
        conn.commit()
        return envelope(_row_to_dict(updated, EVP_COLUMNS))
    except Exception as e:
        logger.error("update_evidence_pack error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
