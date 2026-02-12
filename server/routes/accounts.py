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

ACCOUNT_COLUMNS = [
    "id", "batch_id", "workspace_id", "account_name", "billing_country",
    "billing_city", "account_fingerprint",
    "created_at", "updated_at", "deleted_at", "version", "metadata",
]
ACCOUNT_SELECT = ", ".join(ACCOUNT_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/batches/{bat_id}/accounts")
def list_accounts(
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
            sql = "SELECT %s FROM accounts %s ORDER BY id ASC LIMIT %%s" % (ACCOUNT_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, ACCOUNT_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_accounts error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/batches/{bat_id}/accounts", status_code=201)
def create_account(
    bat_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    account_name = body.get("account_name")
    if not account_name or not isinstance(account_name, str) or not account_name.strip():
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "account_name is required and must be a non-empty string"),
        )
    account_name = account_name.strip()

    billing_country = body.get("billing_country")
    billing_city = body.get("billing_city")
    account_fingerprint = body.get("account_fingerprint")
    metadata = body.get("metadata", {})

    acc_id = generate_id("acc_")

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
                """INSERT INTO accounts
                   (id, batch_id, workspace_id, account_name, billing_country,
                    billing_city, account_fingerprint, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + ACCOUNT_SELECT,
                (acc_id, bat_id, workspace_id, account_name, billing_country,
                 billing_city, account_fingerprint, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="account.created",
                actor_id=auth.user_id,
                resource_type="account",
                resource_id=acc_id,
                batch_id=bat_id,
                detail={"account_name": account_name},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, ACCOUNT_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_account error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/accounts/{acc_id}")
def get_account(
    acc_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM accounts WHERE id = %%s AND deleted_at IS NULL" % ACCOUNT_SELECT,
                (acc_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Account not found: %s" % acc_id),
            )
        return envelope(_row_to_dict(row, ACCOUNT_COLUMNS))
    except Exception as e:
        logger.error("get_account error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/accounts/{acc_id}")
def update_account(
    acc_id: str,
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
    if "account_name" in body:
        n = body["account_name"]
        if not isinstance(n, str) or not n.strip():
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "account_name must be a non-empty string"),
            )
        updates["account_name"] = n.strip()
    if "billing_country" in body:
        updates["billing_country"] = body["billing_country"]
    if "billing_city" in body:
        updates["billing_city"] = body["billing_city"]
    if "account_fingerprint" in body:
        updates["account_fingerprint"] = body["account_fingerprint"]
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
                "SELECT version, deleted_at, workspace_id FROM accounts WHERE id = %s",
                (acc_id,),
            )
            row = cur.fetchone()
            if not row or row[1] is not None:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Account not found: %s" % acc_id),
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
            set_clauses.append("version = version + 1")
            set_clauses.append("updated_at = NOW()")

            params.extend([acc_id, version])
            sql = "UPDATE accounts SET %s WHERE id = %%s AND version = %%s RETURNING %s" % (
                ", ".join(set_clauses),
                ACCOUNT_SELECT,
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
                event_type="account.updated",
                actor_id=auth.user_id,
                resource_type="account",
                resource_id=acc_id,
                detail={"fields": list(updates.keys()), "new_version": version + 1},
            )
        conn.commit()
        return envelope(_row_to_dict(updated, ACCOUNT_COLUMNS))
    except Exception as e:
        logger.error("update_account error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
