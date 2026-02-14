import json
import re
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


def _require_workspace_id(request: Request, auth, conn, body=None):
    ws_id = request.headers.get("X-Workspace-Id", "").strip() or None
    if not ws_id and body and isinstance(body, dict):
        ws_id = body.get("workspace_id")
    if not ws_id and auth.workspace_id:
        ws_id = auth.workspace_id
    if not ws_id:
        return None, JSONResponse(
            status_code=422,
            content=error_envelope(
                "MISSING_WORKSPACE",
                "X-Workspace-Id header or workspace_id field is required",
            ),
        )
    with conn.cursor() as cur:
        cur.execute(
            "SELECT role FROM user_workspace_roles WHERE user_id = %s AND workspace_id = %s",
            (auth.user_id, ws_id),
        )
        if not cur.fetchone():
            return None, JSONResponse(
                status_code=403,
                content=error_envelope("FORBIDDEN", "No access to workspace %s" % ws_id),
            )
    return ws_id, None

TERM_COLUMNS = [
    "id", "workspace_id", "field_key", "display_name", "description",
    "data_type", "category", "is_required",
    "created_at", "updated_at", "deleted_at", "version", "metadata",
]
TERM_SELECT = ", ".join(TERM_COLUMNS)

ALIAS_COLUMNS = [
    "id", "workspace_id", "term_id", "alias", "normalized_alias",
    "source", "created_by", "created_at", "deleted_at", "metadata",
]
ALIAS_SELECT = ", ".join(ALIAS_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


def _normalize_alias(alias):
    s = alias.strip().lower()
    s = re.sub(r'\s+', ' ', s)
    return s


@router.get("/glossary/terms")
def list_glossary_terms(
    request: Request,
    query: str = Query(None),
    category: str = Query(None),
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        ws_id, err = _require_workspace_id(request, auth, conn)
        if err:
            return err

        with conn.cursor() as cur:
            conditions = ["deleted_at IS NULL", "workspace_id = %s"]
            params = [ws_id]

            if query:
                conditions.append("(field_key ILIKE %s OR display_name ILIKE %s OR description ILIKE %s)")
                like_pat = "%%%s%%" % query
                params.extend([like_pat, like_pat, like_pat])
            if category:
                conditions.append("category = %s")
                params.append(category)
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM glossary_terms %s ORDER BY field_key ASC LIMIT %%s" % (
                TERM_SELECT, where
            )
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, TERM_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_glossary_terms error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/glossary/terms", status_code=201)
def create_glossary_term(
    request: Request,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    field_key = body.get("field_key")
    if not field_key or not isinstance(field_key, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "field_key (string) is required"),
        )

    display_name = body.get("display_name", field_key)
    description = body.get("description")
    data_type = body.get("data_type", "string")
    category = body.get("category")
    is_required = body.get("is_required", False)
    metadata = body.get("metadata", {})

    term_id = generate_id("glt_")

    conn = get_conn()
    workspace_id, err = _require_workspace_id(request, auth, conn, body)
    if err:
        put_conn(conn)
        return err
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO glossary_terms
                   (id, workspace_id, field_key, display_name, description,
                    data_type, category, is_required, metadata)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb)
                   RETURNING """ + TERM_SELECT,
                (term_id, workspace_id, field_key, display_name, description,
                 data_type, category, is_required, json.dumps(metadata)),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="glossary_term.created",
                actor_id=auth.user_id,
                resource_type="glossary_term",
                resource_id=term_id,
                detail={"field_key": field_key, "display_name": display_name},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, TERM_COLUMNS)),
        )
    except Exception as e:
        err_str = str(e)
        if "idx_glossary_terms_field_key" in err_str:
            conn.rollback()
            return JSONResponse(
                status_code=409,
                content=error_envelope(
                    "DUPLICATE",
                    "A glossary term with field_key '%s' already exists in this workspace" % field_key,
                ),
            )
        logger.error("create_glossary_term error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/glossary/aliases", status_code=201)
def create_glossary_alias(
    request: Request,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    term_id = body.get("term_id")
    alias = body.get("alias")

    if not term_id or not isinstance(term_id, str):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "term_id (string) is required"),
        )
    if not alias or not isinstance(alias, str) or len(alias.strip()) == 0:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "alias (non-empty string) is required"),
        )

    normalized = _normalize_alias(alias)
    alias_id = generate_id("gla_")

    conn = get_conn()
    try:
        ws_id, err = _require_workspace_id(request, auth, conn, body)
        if err:
            return err

        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, workspace_id FROM glossary_terms WHERE id = %s AND workspace_id = %s AND deleted_at IS NULL",
                (term_id, ws_id),
            )
            term_row = cur.fetchone()
            if not term_row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Glossary term not found: %s" % term_id),
                )
            workspace_id = ws_id

            cur.execute(
                """INSERT INTO glossary_aliases
                   (id, workspace_id, term_id, alias, normalized_alias, source, created_by)
                   VALUES (%s, %s, %s, %s, %s, 'manual', %s)
                   RETURNING """ + ALIAS_SELECT,
                (alias_id, workspace_id, term_id, alias.strip(), normalized, auth.user_id),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="glossary_alias.created",
                actor_id=auth.user_id,
                resource_type="glossary_alias",
                resource_id=alias_id,
                detail={"term_id": term_id, "alias": alias.strip(), "normalized_alias": normalized},
            )
        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope(_row_to_dict(row, ALIAS_COLUMNS)),
        )
    except Exception as e:
        err_str = str(e)
        if "idx_glossary_aliases_normalized" in err_str:
            conn.rollback()
            details = {}
            conn2 = get_conn()
            try:
                with conn2.cursor() as cur2:
                    cur2.execute(
                        """SELECT ga.id, ga.term_id, gt.field_key
                           FROM glossary_aliases ga
                           JOIN glossary_terms gt ON ga.term_id = gt.id
                           WHERE ga.workspace_id = %s AND ga.normalized_alias = %s AND ga.deleted_at IS NULL""",
                        (workspace_id, normalized),
                    )
                    existing = cur2.fetchone()
                if existing:
                    details = {
                        "existing_alias_id": existing[0],
                        "existing_term_id": existing[1],
                        "existing_field_key": existing[2],
                    }
            finally:
                put_conn(conn2)

            return JSONResponse(
                status_code=409,
                content=error_envelope(
                    "DUPLICATE_ALIAS",
                    "Alias '%s' already exists in this workspace" % alias.strip(),
                    details=details,
                ),
            )
        logger.error("create_glossary_alias error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
