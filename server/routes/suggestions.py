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
from server.suggestion_engine import generate_suggestions, generate_suggestions_local

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5")


def _resolve_workspace_id(auth, conn):
    if auth.workspace_id:
        return auth.workspace_id
    with conn.cursor() as cur:
        cur.execute(
            "SELECT workspace_id FROM user_workspace_roles WHERE user_id = %s LIMIT 1",
            (auth.user_id,),
        )
        row = cur.fetchone()
        if row:
            auth.workspace_id = row[0]
            return row[0]
    return None


def _verify_workspace_access(auth, workspace_id, conn):
    with conn.cursor() as cur:
        cur.execute(
            "SELECT role FROM user_workspace_roles WHERE user_id = %s AND workspace_id = %s",
            (auth.user_id, workspace_id),
        )
        return cur.fetchone() is not None

SUGGESTION_COLUMNS = [
    "id", "workspace_id", "run_id", "document_id", "source_field",
    "suggested_term_id", "match_score", "match_method", "status",
    "resolved_by", "resolved_at", "candidates", "created_at", "version", "metadata",
]
SUGGESTION_SELECT = ", ".join(SUGGESTION_COLUMNS)

RUN_COLUMNS = [
    "id", "workspace_id", "document_id", "status",
    "total_suggestions", "created_at", "completed_at", "created_by", "metadata",
]
RUN_SELECT = ", ".join(RUN_COLUMNS)


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
    import re
    s = alias.strip().lower()
    s = re.sub(r'\s+', ' ', s)
    return s


@router.post("/documents/{document_id}/suggestion-runs", status_code=201)
async def create_suggestion_run(
    document_id: str,
    request: Request,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    body = {}

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, workspace_id FROM documents WHERE id = %s AND deleted_at IS NULL",
                (document_id,),
            )
            doc_row = cur.fetchone()

            workspace_id = None
            run_mode = "db_backed"

            if doc_row:
                workspace_id = doc_row[1]
                if not _verify_workspace_access(auth, workspace_id, conn):
                    return JSONResponse(
                        status_code=404,
                        content=error_envelope("NOT_FOUND", "Document not found: %s" % document_id),
                    )
            else:
                workspace_id = _resolve_workspace_id(auth, conn)
                if not workspace_id:
                    return JSONResponse(
                        status_code=400,
                        content=error_envelope("NO_WORKSPACE", "Cannot resolve workspace for local fallback"),
                    )
                run_mode = "local_fallback"

            run_id = generate_id("sgr_")

            cur.execute(
                """INSERT INTO suggestion_runs
                   (id, workspace_id, document_id, status, created_by)
                   VALUES (%s, %s, %s, 'running', %s)""",
                (run_id, workspace_id, document_id, auth.user_id),
            )

            try:
                if run_mode == "db_backed":
                    suggestions, diagnostics, suppressed = generate_suggestions(cur, workspace_id, document_id)
                else:
                    source_fields = []
                    diagnostics = {"run_mode": "local_fallback"}
                    suggestions, diagnostics, suppressed = generate_suggestions_local(cur, workspace_id, source_fields)
            except Exception as e:
                logger.error("[SUGGEST] Engine error: %s", e)
                cur.execute(
                    """UPDATE suggestion_runs SET status = 'failed',
                       completed_at = NOW(), metadata = %s::jsonb
                       WHERE id = %s""",
                    (json.dumps({"error": str(e)}), run_id),
                )
                conn.commit()
                return JSONResponse(
                    status_code=500,
                    content=error_envelope("SUGGESTION_ENGINE_FAILED", str(e)),
                )

            for s in suggestions:
                sug_id = generate_id("sug_")
                sug_meta = s.pop("_meta", None)
                match_context = s.pop("_match_context", None)
                if sug_meta is None:
                    sug_meta = {}
                if match_context:
                    sug_meta["_match_context"] = match_context
                cur.execute(
                    """INSERT INTO suggestions
                       (id, workspace_id, run_id, document_id, source_field,
                        suggested_term_id, match_score, match_method, candidates, metadata)
                       VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)""",
                    (sug_id, workspace_id, run_id, document_id,
                     s["source_field"], s["suggested_term_id"],
                     s["match_score"], s["match_method"],
                     json.dumps(s["candidates"]),
                     json.dumps(sug_meta) if sug_meta else None),
                )

            now_iso = datetime.now(timezone.utc).isoformat()
            run_metadata = json.dumps(diagnostics) if diagnostics else None
            cur.execute(
                """UPDATE suggestion_runs
                   SET status = 'completed', total_suggestions = %s, completed_at = %s,
                       metadata = %s::jsonb
                   WHERE id = %s
                   RETURNING """ + RUN_SELECT,
                (len(suggestions), now_iso, run_metadata, run_id),
            )
            run_row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=workspace_id,
                event_type="suggestion_run.created",
                actor_id=auth.user_id,
                resource_type="suggestion_run",
                resource_id=run_id,
                detail={
                    "document_id": document_id,
                    "total_suggestions": len(suggestions),
                    "run_mode": diagnostics.get("run_mode", "unknown") if diagnostics else "unknown",
                },
            )
        conn.commit()

        result = _row_to_dict(run_row, RUN_COLUMNS)
        if diagnostics:
            result["diagnostics"] = diagnostics

        return JSONResponse(
            status_code=201,
            content=envelope(result),
        )
    except Exception as e:
        logger.error("create_suggestion_run error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/suggestion-runs/local", status_code=201)
async def create_local_suggestion_run(
    request: Request,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        body = {}
        try:
            content_type = request.headers.get("content-type", "")
            if "json" in content_type:
                body = await request.json()
        except Exception:
            body = {}

        source_fields = body.get("source_fields", []) if isinstance(body, dict) else []
        body_text = body.get("body_text", None) if isinstance(body, dict) else None
        document_id = body.get("document_id", "local_" + generate_id("doc_")) if isinstance(body, dict) else "local_" + generate_id("doc_")

        workspace_id = _resolve_workspace_id(auth, conn)
        if not workspace_id:
            return JSONResponse(
                status_code=400,
                content=error_envelope("NO_WORKSPACE", "Cannot resolve workspace"),
            )

        if not source_fields and not body_text:
            return JSONResponse(
                status_code=400,
                content=error_envelope("VALIDATION_ERROR", "source_fields array or body_text is required for local runs"),
            )

        with conn.cursor() as cur:
            try:
                suggestions, diagnostics, suppressed = generate_suggestions_local(cur, workspace_id, source_fields, body_text=body_text)
            except Exception as e:
                logger.error("[SUGGEST] Local engine error: %s", e)
                return JSONResponse(
                    status_code=500,
                    content=error_envelope("SUGGESTION_ENGINE_FAILED", str(e)),
                )

            now_iso = datetime.now(timezone.utc).isoformat()
            run_id = generate_id("sgr_")

            sug_results = []
            for s in suggestions:
                sug_id = generate_id("sug_")
                sug_meta = s.pop("_meta", None)
                sug_results.append({
                    "id": sug_id,
                    "workspace_id": workspace_id,
                    "run_id": run_id,
                    "document_id": document_id,
                    "source_field": s["source_field"],
                    "suggested_term_id": s.get("suggested_term_id"),
                    "suggested_label": s.get("suggested_label"),
                    "glossary_term_id": s.get("glossary_term_id"),
                    "glossary_field_key": s.get("glossary_field_key"),
                    "matched_text": s.get("matched_text", s["source_field"]),
                    "confidence_score": s.get("confidence_score", s.get("match_score", 0)),
                    "confidence_pct": s.get("confidence_pct", 0),
                    "confidence_bucket": s.get("confidence_bucket", "HIDDEN"),
                    "match_score": s.get("match_score", 0),
                    "match_method": s.get("match_method", "none"),
                    "match_reason": s.get("match_reason", ""),
                    "reason_labels": s.get("reason_labels", []),
                    "status": "pending",
                    "resolved_by": None,
                    "resolved_at": None,
                    "candidates": s.get("candidates", []),
                    "_components": s.get("_components"),
                    "_match_context": s.get("_match_context"),
                    "matched_tokens": s.get("matched_tokens", []),
                    "entity_eligible": s.get("entity_eligible", False),
                    "candidate_source": s.get("candidate_source", "header"),
                    "created_at": now_iso,
                    "version": 1,
                    "metadata": sug_meta,
                })

        result = {
            "id": run_id,
            "workspace_id": workspace_id,
            "document_id": document_id,
            "status": "completed",
            "total_suggestions": len(suggestions),
            "created_at": now_iso,
            "completed_at": now_iso,
            "created_by": auth.user_id,
            "metadata": {"run_mode": "local_fallback"},
            "diagnostics": diagnostics,
            "suggestions": sug_results,
            "suppressed": [
                {
                    "source_field": s["source_field"],
                    "suppression_reasons": s.get("suppression_reasons", []),
                    "entity_eligible": s.get("entity_eligible", False),
                    "confidence_pct": s.get("confidence_pct", 0),
                    "confidence_bucket": s.get("confidence_bucket", "HIDDEN"),
                    "candidates": s.get("candidates", []),
                }
                for s in suppressed
            ],
        }

        return JSONResponse(
            status_code=201,
            content=envelope(result),
        )
    except Exception as e:
        logger.error("create_local_suggestion_run error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/documents/{document_id}/suggestions")
def list_suggestions(
    document_id: str,
    status: str = Query(None),
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, workspace_id FROM documents WHERE id = %s AND deleted_at IS NULL",
                (document_id,),
            )
            doc_row = cur.fetchone()

            if doc_row:
                doc_ws = doc_row[1]
                if not _verify_workspace_access(auth, doc_ws, conn):
                    return JSONResponse(
                        status_code=404,
                        content=error_envelope("NOT_FOUND", "Document not found: %s" % document_id),
                    )
            else:
                doc_ws = _resolve_workspace_id(auth, conn)
                if not doc_ws:
                    return JSONResponse(
                        status_code=404,
                        content=error_envelope("NOT_FOUND", "Document not found: %s" % document_id),
                    )

            conditions = ["document_id = %s", "workspace_id = %s"]
            params: list = [document_id, doc_ws]

            if status:
                conditions.append("status = %s")
                params.append(status)
            if cursor:
                conditions.append("id > %s")
                params.append(cursor)

            where = "WHERE " + " AND ".join(conditions)
            sql = "SELECT %s FROM suggestions %s ORDER BY id ASC LIMIT %%s" % (
                SUGGESTION_SELECT, where
            )
            params.append(limit + 1)

            cur.execute(sql, params)
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = [_row_to_dict(r, SUGGESTION_COLUMNS) for r in rows]
        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("list_suggestions error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.patch("/suggestions/{suggestion_id}")
def update_suggestion(
    suggestion_id: str,
    body: dict,
    auth=Depends(require_auth(AuthClass.BEARER)),
):
    if isinstance(auth, JSONResponse):
        return auth

    new_status = body.get("status")
    version = body.get("version")
    selected_term_id = body.get("selected_term_id")

    if new_status not in ("accepted", "rejected", "dismissed"):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "status must be one of: accepted, rejected, dismissed"),
        )
    if version is None or not isinstance(version, int):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "version (integer) is required for PATCH"),
        )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT %s FROM suggestions WHERE id = %%s" % SUGGESTION_SELECT,
                (suggestion_id,),
            )
            row = cur.fetchone()
            if not row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Suggestion not found: %s" % suggestion_id),
                )

            sug_ws = row[1]
            if not _verify_workspace_access(auth, sug_ws, conn):
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "Suggestion not found: %s" % suggestion_id),
                )

            sug = _row_to_dict(row, SUGGESTION_COLUMNS)
            if sug["version"] != version:
                return JSONResponse(
                    status_code=409,
                    content=error_envelope(
                        "STALE_VERSION",
                        "Resource has been modified since your last read",
                        details={"current_version": sug["version"], "provided_version": version},
                    ),
                )

            if sug["status"] != "pending":
                return JSONResponse(
                    status_code=400,
                    content=error_envelope("INVALID_STATE", "Suggestion is already %s" % sug["status"]),
                )

            now_iso = datetime.now(timezone.utc).isoformat()
            term_id = selected_term_id or sug["suggested_term_id"]

            cur.execute(
                """UPDATE suggestions
                   SET status = %s, resolved_by = %s, resolved_at = %s,
                       version = version + 1, suggested_term_id = COALESCE(%s, suggested_term_id)
                   WHERE id = %s AND version = %s
                   RETURNING """ + SUGGESTION_SELECT,
                (new_status, auth.user_id, now_iso, selected_term_id,
                 suggestion_id, version),
            )
            updated = cur.fetchone()
            if not updated:
                conn.rollback()
                return JSONResponse(
                    status_code=409,
                    content=error_envelope("STALE_VERSION", "Concurrent modification detected"),
                )

            alias_id = None
            if new_status == "accepted" and term_id:
                source_field = sug["source_field"]
                normalized = _normalize_alias(source_field)

                cur.execute(
                    """SELECT id FROM glossary_aliases
                       WHERE workspace_id = %s AND normalized_alias = %s AND deleted_at IS NULL""",
                    (sug["workspace_id"], normalized),
                )
                existing = cur.fetchone()
                if existing:
                    alias_id = existing[0]
                else:
                    alias_id = generate_id("gla_")
                    cur.execute(
                        """INSERT INTO glossary_aliases
                           (id, workspace_id, term_id, alias, normalized_alias, source, created_by)
                           VALUES (%s, %s, %s, %s, %s, 'suggestion', %s)""",
                        (alias_id, sug["workspace_id"], term_id,
                         source_field, normalized, auth.user_id),
                    )
                    emit_audit_event(
                        cur,
                        workspace_id=sug["workspace_id"],
                        event_type="glossary_alias.created",
                        actor_id=auth.user_id,
                        resource_type="glossary_alias",
                        resource_id=alias_id,
                        detail={"term_id": term_id, "alias": source_field, "normalized_alias": normalized},
                    )

            event_type = "suggestion.%s" % new_status
            emit_audit_event(
                cur,
                workspace_id=sug["workspace_id"],
                event_type=event_type,
                actor_id=auth.user_id,
                resource_type="suggestion",
                resource_id=suggestion_id,
                detail={
                    "source_field": sug["source_field"],
                    "term_id": term_id,
                    "alias_id": alias_id,
                },
            )
        conn.commit()

        result = _row_to_dict(updated, SUGGESTION_COLUMNS)
        if alias_id:
            result["alias_id"] = alias_id

        return envelope(result)
    except Exception as e:
        logger.error("update_suggestion error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
