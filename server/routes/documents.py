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

DOCUMENT_COLUMNS = [
    "id", "contract_id", "batch_id", "workspace_id", "document_fingerprint",
    "file_url", "file_name", "section_name",
    "created_at", "updated_at", "deleted_at", "version", "metadata",
]
DOCUMENT_SELECT = ", ".join(DOCUMENT_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


@router.get("/contracts/{ctr_id}/documents")
def list_documents(
    ctr_id: str,
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
                "SELECT id, workspace_id FROM contracts WHERE id = %s AND deleted_at IS NULL",
                (ctr_id,),
            )
            ctr_row = cur.fetchone()
            if not ctr_row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Contract not found: %s" % ctr_id),
                )

            conditions = ["contract_id = %s"]
            params = [ctr_id]

            if not include_deleted:
                conditions.append("deleted_at IS NULL")
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM documents %s ORDER BY id ASC LIMIT %%s" % (DOCUMENT_SELECT, where)
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, DOCUMENT_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_documents error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/contracts/{ctr_id}/documents", status_code=201)
def create_document(
    ctr_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    document_fingerprint = body.get("document_fingerprint")
    file_url = body.get("file_url")
    file_name = body.get("file_name")
    section_name = body.get("section_name")
    metadata = body.get("metadata", {})

    doc_id = generate_id("doc_")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, workspace_id, batch_id FROM contracts WHERE id = %s AND deleted_at IS NULL",
                (ctr_id,),
            )
            ctr_row = cur.fetchone()
            if not ctr_row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Contract not found: %s" % ctr_id),
                )
            workspace_id = ctr_row[1]
            batch_id = ctr_row[2]

            cur.execute(
                """INSERT INTO documents
                   (id, contract_id, batch_id, workspace_id, document_fingerprint,
                    file_url, file_name, section_name, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + DOCUMENT_SELECT,
                (doc_id, ctr_id, batch_id, workspace_id, document_fingerprint,
                 file_url, file_name, section_name, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="document.created",
                actor_id=auth.user_id,
                resource_type="document",
                resource_id=doc_id,
                batch_id=batch_id,
                detail={"file_name": file_name, "contract_id": ctr_id},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, DOCUMENT_COLUMNS)),
        )
    except Exception as e:
        logger.error("create_document error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/documents/{doc_id}")
def get_document(
    doc_id: str,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM documents WHERE id = %%s AND deleted_at IS NULL" % DOCUMENT_SELECT,
                (doc_id,),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(
                status_code=404,
                content=error_envelope("NOT_FOUND", "Document not found: %s" % doc_id),
            )
        return envelope(_row_to_dict(row, DOCUMENT_COLUMNS))
    except Exception as e:
        logger.error("get_document error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/documents/{doc_id}")
def update_document(
    doc_id: str,
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
    if "document_fingerprint" in body:
        updates["document_fingerprint"] = body["document_fingerprint"]
    if "file_url" in body:
        updates["file_url"] = body["file_url"]
    if "file_name" in body:
        updates["file_name"] = body["file_name"]
    if "section_name" in body:
        updates["section_name"] = body["section_name"]
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
                "SELECT version, deleted_at, workspace_id FROM documents WHERE id = %s",
                (doc_id,),
            )
            row = cur.fetchone()
            if not row or row[1] is not None:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Document not found: %s" % doc_id),
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

            params.extend([doc_id, version])
            sql = "UPDATE documents SET %s WHERE id = %%s AND version = %%s RETURNING %s" % (
                ", ".join(set_clauses),
                DOCUMENT_SELECT,
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
                event_type="document.updated",
                actor_id=auth.user_id,
                resource_type="document",
                resource_id=doc_id,
                detail={"fields": list(updates.keys()), "new_version": version + 1},
            )
        conn.commit()
        return envelope(_row_to_dict(updated, DOCUMENT_COLUMNS))
    except Exception as e:
        logger.error("update_document error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
