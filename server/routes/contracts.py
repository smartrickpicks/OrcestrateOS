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
from server.contract_health_runtime import decorate_contract_health

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")

ALLOWED_STATUSES = ("active", "archived", "review", "flagged")

CONTRACT_COLUMNS = [
    "id", "batch_id", "account_id", "workspace_id", "contract_fingerprint",
    "contract_id_source", "file_url", "file_name", "status", "health_score",
    "created_at", "updated_at", "deleted_at", "version", "metadata",
]
CONTRACT_SELECT = ", ".join(CONTRACT_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/batches/{bat_id}/contracts")
def list_contracts(
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
            sql = "SELECT %s FROM contracts %s ORDER BY id ASC LIMIT %%s" % (CONTRACT_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [decorate_contract_health(_row_to_dict(r, CONTRACT_COLUMNS)) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_contracts error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/batches/{bat_id}/contracts", status_code=201)
def create_contract(
    bat_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    contract_fingerprint = body.get("contract_fingerprint")
    contract_id_source = body.get("contract_id_source")
    file_url = body.get("file_url")
    file_name = body.get("file_name")
    status = body.get("status", "active")
    account_id = body.get("account_id")
    health_score = body.get("health_score")
    metadata = body.get("metadata", {})

    if health_score is not None and not isinstance(health_score, int):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "health_score must be an integer"),
        )

    ctr_id = generate_id("ctr_")

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

            if account_id:
                cur.execute(
                    "SELECT id FROM accounts WHERE id = %s AND deleted_at IS NULL",
                    (account_id,),
                )
                if not cur.fetchone():
                    return JSONResponse(
                        status_code=404,
                        content=error_envelope("NOT_FOUND", "Account not found: %s" % account_id),
                    )

            cur.execute(
                """INSERT INTO contracts
                   (id, batch_id, account_id, workspace_id, contract_fingerprint,
                    contract_id_source, file_url, file_name, status, health_score, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + CONTRACT_SELECT,
                (ctr_id, bat_id, account_id, workspace_id, contract_fingerprint,
                 contract_id_source, file_url, file_name, status, health_score,
                 json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="contract.created",
                actor_id=auth.user_id,
                resource_type="contract",
                resource_id=ctr_id,
                batch_id=bat_id,
                detail={"file_name": file_name, "status": status},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(decorate_contract_health(_row_to_dict(row, CONTRACT_COLUMNS))),
        )
    except Exception as e:
        logger.error("create_contract error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/contracts/{ctr_id}")
def get_contract(
    ctr_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM contracts WHERE id = %%s AND deleted_at IS NULL" % CONTRACT_SELECT,
                (ctr_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Contract not found: %s" % ctr_id),
            )
        return envelope(decorate_contract_health(_row_to_dict(row, CONTRACT_COLUMNS)))
    except Exception as e:
        logger.error("get_contract error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/contracts/{ctr_id}")
def update_contract(
    ctr_id: str,
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
    if "contract_fingerprint" in body:
        updates["contract_fingerprint"] = body["contract_fingerprint"]
    if "contract_id_source" in body:
        updates["contract_id_source"] = body["contract_id_source"]
    if "file_url" in body:
        updates["file_url"] = body["file_url"]
    if "file_name" in body:
        updates["file_name"] = body["file_name"]
    if "status" in body:
        if body["status"] not in ALLOWED_STATUSES:
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "status must be one of: %s" % ", ".join(ALLOWED_STATUSES)),
            )
        updates["status"] = body["status"]
    if "account_id" in body:
        updates["account_id"] = body["account_id"]
    if "health_score" in body:
        val = body["health_score"]
        if val is not None and not isinstance(val, int):
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "health_score must be an integer or null"),
            )
        updates["health_score"] = val
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
                "SELECT version, deleted_at, workspace_id FROM contracts WHERE id = %s",
                (ctr_id,),
            )
            row = cur.fetchone()
            if not row or row[1] is not None:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Contract not found: %s" % ctr_id),
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

            if "account_id" in updates and updates["account_id"] is not None:
                cur.execute(
                    "SELECT id FROM accounts WHERE id = %s AND deleted_at IS NULL",
                    (updates["account_id"],),
                )
                if not cur.fetchone():
                    return JSONResponse(
                        status_code=404,
                        content=error_envelope("NOT_FOUND", "Account not found: %s" % updates["account_id"]),
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

            params.extend([ctr_id, version])
            sql = "UPDATE contracts SET %s WHERE id = %%s AND version = %%s RETURNING %s" % (
                ", ".join(set_clauses),
                CONTRACT_SELECT,
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
                event_type="contract.updated",
                actor_id=auth.user_id,
                resource_type="contract",
                resource_id=ctr_id,
                detail={"fields": list(updates.keys()), "new_version": version + 1},
            )
        conn.commit()
        return envelope(decorate_contract_health(_row_to_dict(updated, CONTRACT_COLUMNS)))
    except Exception as e:
        logger.error("update_contract error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
