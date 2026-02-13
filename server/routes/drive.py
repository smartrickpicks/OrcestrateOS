import json
import logging
import os
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.ulid import generate_id
from server.api_v25 import envelope, collection_envelope, error_envelope
from server.auth import AuthClass, require_auth, require_role, Role
from server.audit import emit_audit_event

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/v2.5", tags=["drive"])

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_OAUTH_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_OAUTH_CLIENT_SECRET", "")

DRIVE_SCOPES = [
    "https://www.googleapis.com/auth/drive.readonly",
    "https://www.googleapis.com/auth/drive.file",
    "openid",
    "https://www.googleapis.com/auth/userinfo.email",
    "https://www.googleapis.com/auth/userinfo.profile",
]

MAX_IMPORT_SIZE_BYTES = 50 * 1024 * 1024

CONN_COLUMNS = [
    "id", "workspace_id", "connected_by", "drive_email",
    "status", "connected_at", "updated_at", "metadata",
]
CONN_SELECT = ", ".join(CONN_COLUMNS)

PROV_COLUMNS = [
    "id", "workspace_id", "source_file_id", "source_file_name",
    "source_mime_type", "source_size_bytes", "drive_id",
    "drive_modified_time", "drive_md5", "version_number",
    "supersedes_id", "imported_by", "imported_at", "batch_id", "metadata",
]
PROV_SELECT = ", ".join(PROV_COLUMNS)


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


def _get_drive_service(access_token):
    from google.oauth2.credentials import Credentials
    from googleapiclient.discovery import build
    creds = Credentials(token=access_token)
    return build("drive", "v3", credentials=creds, cache_discovery=False)


def _refresh_token_if_needed(conn_row, db_conn):
    token_expiry = conn_row[6] if len(conn_row) > 6 else None
    access_token = conn_row[4] if len(conn_row) > 4 else None
    refresh_token = conn_row[5] if len(conn_row) > 5 else None
    conn_id = conn_row[0]

    if token_expiry and token_expiry.replace(tzinfo=timezone.utc) > datetime.now(timezone.utc):
        return access_token

    if not refresh_token:
        return access_token

    try:
        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request as GoogleRequest
        creds = Credentials(
            token=access_token,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=GOOGLE_CLIENT_ID,
            client_secret=GOOGLE_CLIENT_SECRET,
            scopes=DRIVE_SCOPES,
        )
        creds.refresh(GoogleRequest())
        new_token = creds.token
        new_expiry = creds.expiry

        with db_conn.cursor() as cur:
            cur.execute(
                """UPDATE drive_connections
                   SET access_token = %s, token_expiry = %s, updated_at = NOW()
                   WHERE id = %s""",
                (new_token, new_expiry, conn_id),
            )
        db_conn.commit()
        return new_token
    except Exception as e:
        logger.error("Token refresh failed for connection %s: %s", conn_id, e)
        return access_token


def _get_workspace_connection(ws_id, db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """SELECT id, workspace_id, connected_by, drive_email,
                      access_token, refresh_token, token_expiry,
                      status, connected_at, updated_at, metadata
               FROM drive_connections
               WHERE workspace_id = %s AND status = 'active'""",
            (ws_id,),
        )
        return cur.fetchone()


@router.post("/workspaces/{ws_id}/drive/connect")
async def drive_connect(ws_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return JSONResponse(
            status_code=500,
            content=error_envelope("CONFIG_ERROR", "Google Drive OAuth is not configured on the server"),
        )

    try:
        body = await request.json()
    except Exception:
        body = {}

    redirect_uri = body.get("redirect_uri", "").strip()
    if not redirect_uri:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "redirect_uri is required"),
        )

    from google_auth_oauthlib.flow import Flow
    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=DRIVE_SCOPES,
        redirect_uri=redirect_uri,
    )

    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=json.dumps({"workspace_id": ws_id, "user_id": auth.user_id}),
    )

    return envelope({
        "auth_url": auth_url,
        "state": state,
    })


@router.post("/workspaces/{ws_id}/drive/callback")
async def drive_callback(ws_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid JSON body"),
        )

    code = body.get("code", "").strip()
    redirect_uri = body.get("redirect_uri", "").strip()

    if not code or not redirect_uri:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "code and redirect_uri are required"),
        )

    try:
        from google_auth_oauthlib.flow import Flow
        flow = Flow.from_client_config(
            {
                "web": {
                    "client_id": GOOGLE_CLIENT_ID,
                    "client_secret": GOOGLE_CLIENT_SECRET,
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                }
            },
            scopes=DRIVE_SCOPES,
            redirect_uri=redirect_uri,
        )
        flow.fetch_token(code=code)
        credentials = flow.credentials
    except Exception as e:
        logger.error("Drive OAuth token exchange failed: %s", e)
        return JSONResponse(
            status_code=401,
            content=error_envelope("UNAUTHORIZED", "Failed to exchange authorization code"),
        )

    drive_email = ""
    try:
        service = _get_drive_service(credentials.token)
        about = service.about().get(fields="user(emailAddress)").execute()
        drive_email = about.get("user", {}).get("emailAddress", "")
    except Exception as e:
        logger.warning("Could not fetch Drive email: %s", e)

    conn_id = generate_id("drc_")
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO drive_connections
                   (id, workspace_id, connected_by, drive_email,
                    access_token, refresh_token, token_expiry, status)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, 'active')
                   ON CONFLICT ON CONSTRAINT uq_drive_connections_workspace
                   DO UPDATE SET
                       connected_by = EXCLUDED.connected_by,
                       drive_email = EXCLUDED.drive_email,
                       access_token = EXCLUDED.access_token,
                       refresh_token = EXCLUDED.refresh_token,
                       token_expiry = EXCLUDED.token_expiry,
                       status = 'active',
                       updated_at = NOW()
                   RETURNING """ + CONN_SELECT,
                (conn_id, ws_id, auth.user_id, drive_email,
                 credentials.token, credentials.refresh_token, credentials.expiry),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="DRIVE_CONNECTED",
                actor_id=auth.user_id,
                actor_role=auth.role,
                resource_type="drive_connection",
                resource_id=row[0],
                detail={"drive_email": drive_email},
            )
        conn.commit()
        return envelope(_row_to_dict(row, CONN_COLUMNS))
    except Exception as e:
        logger.error("drive_callback error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.delete("/workspaces/{ws_id}/drive/disconnect")
def drive_disconnect(ws_id: str, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE drive_connections SET status = 'revoked', updated_at = NOW()
                   WHERE workspace_id = %s AND status = 'active'
                   RETURNING """ + CONN_SELECT,
                (ws_id,),
            )
            row = cur.fetchone()

            if not row:
                return JSONResponse(
                    status_code=404,
                    content=error_envelope("NOT_FOUND", "No active Drive connection for this workspace"),
                )

            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="DRIVE_DISCONNECTED",
                actor_id=auth.user_id,
                actor_role=auth.role,
                resource_type="drive_connection",
                resource_id=row[0],
                detail={"drive_email": row[3]},
            )
        conn.commit()
        return envelope(_row_to_dict(row, CONN_COLUMNS))
    except Exception as e:
        logger.error("drive_disconnect error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/workspaces/{ws_id}/drive/status")
def drive_status(ws_id: str, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    conn = get_conn()
    try:
        conn_row = _get_workspace_connection(ws_id, conn)
        if not conn_row:
            return envelope({"connected": False, "drive_email": None, "connection": None})

        return envelope({
            "connected": conn_row[7] == "active",
            "drive_email": conn_row[3],
            "connection": {
                "id": conn_row[0],
                "connected_by": conn_row[2],
                "connected_at": conn_row[8].isoformat() if conn_row[8] else None,
                "status": conn_row[7],
            },
        })
    except Exception as e:
        logger.error("drive_status error: %s", e)
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/workspaces/{ws_id}/drive/browse")
def drive_browse(
    ws_id: str,
    auth=Depends(require_auth(AuthClass.BEARER)),
    parent: str = Query(None),
    drive_id: str = Query(None),
    page_token: str = Query(None),
    page_size: int = Query(50, ge=1, le=200),
):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    conn = get_conn()
    try:
        conn_row = _get_workspace_connection(ws_id, conn)
        if not conn_row:
            return JSONResponse(
                status_code=400,
                content=error_envelope("NO_DRIVE_CONNECTION", "No active Drive connection for this workspace"),
            )

        access_token = _refresh_token_if_needed(conn_row, conn)
        service = _get_drive_service(access_token)

        if parent is None and drive_id is None:
            results = service.drives().list(pageSize=page_size, pageToken=page_token).execute()
            drives = results.get("drives", [])
            return envelope({
                "type": "drives",
                "items": [{"id": d["id"], "name": d["name"], "kind": "drive"} for d in drives],
                "next_page_token": results.get("nextPageToken"),
            })

        q_parts = []
        if parent:
            q_parts.append("'%s' in parents" % parent)
        else:
            q_parts.append("'root' in parents")

        q_parts.append("trashed = false")
        q_parts.append(
            "(mimeType = 'application/vnd.google-apps.folder'"
            " or mimeType = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'"
            " or mimeType = 'application/vnd.ms-excel'"
            " or mimeType = 'text/csv')"
        )
        q = " and ".join(q_parts)

        kwargs = {
            "q": q,
            "pageSize": page_size,
            "fields": "nextPageToken, files(id, name, mimeType, modifiedTime, size, parents)",
            "orderBy": "folder, name",
            "supportsAllDrives": True,
            "includeItemsFromAllDrives": True,
        }
        if page_token:
            kwargs["pageToken"] = page_token
        if drive_id:
            kwargs["driveId"] = drive_id
            kwargs["corpora"] = "drive"

        results = service.files().list(**kwargs).execute()
        files = results.get("files", [])

        items = []
        for f in files:
            items.append({
                "id": f["id"],
                "name": f["name"],
                "mime_type": f["mimeType"],
                "modified_time": f.get("modifiedTime"),
                "size": int(f["size"]) if "size" in f else None,
                "kind": "folder" if f["mimeType"] == "application/vnd.google-apps.folder" else "file",
            })

        db_conn2 = get_conn()
        try:
            with db_conn2.cursor() as cur:
                emit_audit_event(
                    cur,
                    workspace_id=ws_id,
                    event_type="DRIVE_FILE_BROWSED",
                    actor_id=auth.user_id,
                    actor_role=auth.role,
                    detail={"parent": parent, "drive_id": drive_id, "result_count": len(items)},
                )
            db_conn2.commit()
        except Exception:
            db_conn2.rollback()
        finally:
            put_conn(db_conn2)

        return envelope({
            "type": "files",
            "parent": parent,
            "drive_id": drive_id,
            "items": items,
            "next_page_token": results.get("nextPageToken"),
        })

    except Exception as e:
        logger.error("drive_browse error: %s", e)
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/workspaces/{ws_id}/drive/import")
async def drive_import(ws_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid JSON body"),
        )

    file_id = body.get("file_id", "").strip()
    if not file_id:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "file_id is required"),
        )

    conn = get_conn()
    try:
        conn_row = _get_workspace_connection(ws_id, conn)
        if not conn_row:
            return JSONResponse(
                status_code=400,
                content=error_envelope("NO_DRIVE_CONNECTION", "No active Drive connection for this workspace"),
            )

        access_token = _refresh_token_if_needed(conn_row, conn)
        service = _get_drive_service(access_token)

        file_meta = service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, size, modifiedTime, md5Checksum, parents",
            supportsAllDrives=True,
        ).execute()

        file_size = int(file_meta.get("size", 0))
        if file_size > MAX_IMPORT_SIZE_BYTES:
            return JSONResponse(
                status_code=413,
                content=error_envelope(
                    "FILE_TOO_LARGE",
                    "File exceeds 50MB limit (%d bytes)" % file_size,
                    details={"size_bytes": file_size, "max_bytes": MAX_IMPORT_SIZE_BYTES},
                ),
            )

        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, version_number FROM drive_import_provenance
                   WHERE workspace_id = %s AND source_file_id = %s
                   ORDER BY version_number DESC LIMIT 1""",
                (ws_id, file_id),
            )
            prev = cur.fetchone()

            if prev:
                new_version = prev[1] + 1
                supersedes_id = prev[0]
                is_refresh = True
            else:
                new_version = 1
                supersedes_id = None
                is_refresh = False

            prov_id = generate_id("drv_")
            drive_id_val = file_meta.get("parents", [None])[0] if file_meta.get("parents") else None

            cur.execute(
                """INSERT INTO drive_import_provenance
                   (id, workspace_id, source_file_id, source_file_name,
                    source_mime_type, source_size_bytes, drive_id,
                    drive_modified_time, drive_md5,
                    version_number, supersedes_id, imported_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + PROV_SELECT,
                (prov_id, ws_id, file_id, file_meta.get("name"),
                 file_meta.get("mimeType"), file_size, drive_id_val,
                 file_meta.get("modifiedTime"), file_meta.get("md5Checksum"),
                 new_version, supersedes_id, auth.user_id),
            )
            prov_row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="DRIVE_FILE_IMPORTED",
                actor_id=auth.user_id,
                actor_role=auth.role,
                resource_type="drive_import_provenance",
                resource_id=prov_id,
                detail={
                    "source_file_id": file_id,
                    "file_name": file_meta.get("name"),
                    "version_number": new_version,
                    "supersedes_id": supersedes_id,
                    "is_refresh": is_refresh,
                    "size_bytes": file_size,
                },
            )
        conn.commit()

        result = _row_to_dict(prov_row, PROV_COLUMNS)
        result["is_refresh"] = is_refresh

        return JSONResponse(status_code=201, content=envelope(result))

    except Exception as e:
        logger.error("drive_import error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/workspaces/{ws_id}/drive/import-history")
def drive_import_history(
    ws_id: str,
    auth=Depends(require_auth(AuthClass.BEARER)),
    source_file_id: str = Query(...),
    cursor: str = Query(None),
    limit: int = Query(50, ge=1, le=200),
):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT MAX(version_number) FROM drive_import_provenance
                   WHERE workspace_id = %s AND source_file_id = %s""",
                (ws_id, source_file_id),
            )
            max_ver_row = cur.fetchone()
            max_version = max_ver_row[0] if max_ver_row and max_ver_row[0] else 0

            conditions = ["workspace_id = %s", "source_file_id = %s"]
            params = [ws_id, source_file_id]

            if cursor:
                conditions.append("id < %s")
                params.append(cursor)

            where = " AND ".join(conditions)
            params.append(limit + 1)

            cur.execute(
                """SELECT %s FROM drive_import_provenance
                   WHERE %s
                   ORDER BY version_number DESC
                   LIMIT %%s""" % (PROV_SELECT, where),
                params,
            )
            rows = cur.fetchall()

        has_more = len(rows) > limit
        if has_more:
            rows = rows[:limit]

        items = []
        for r in rows:
            d = _row_to_dict(r, PROV_COLUMNS)
            d["is_current"] = (d["version_number"] == max_version)
            items.append(d)

        next_cursor = items[-1]["id"] if items and has_more else None

        return collection_envelope(items, cursor=next_cursor, has_more=has_more, limit=limit)
    except Exception as e:
        logger.error("drive_import_history error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/workspaces/{ws_id}/drive/export")
async def drive_export(ws_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid JSON body"),
        )

    file_name = body.get("file_name", "").strip()
    folder_id = body.get("folder_id", "").strip()
    export_status = body.get("status", "IN_PROGRESS")

    if not file_name:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "file_name is required"),
        )

    conn = get_conn()
    try:
        conn_row = _get_workspace_connection(ws_id, conn)
        if not conn_row:
            return JSONResponse(
                status_code=400,
                content=error_envelope("NO_DRIVE_CONNECTION", "No active Drive connection for this workspace"),
            )

        access_token = _refresh_token_if_needed(conn_row, conn)

        from datetime import date
        date_suffix = date.today().strftime("%Y-%m-%d")
        final_name = "[%s] %s_%s.xlsx" % (export_status, file_name.replace(".xlsx", ""), date_suffix)

        event_type = "DRIVE_EXPORT_FINALIZED" if export_status in ("VERIFIED", "APPROVED") else "DRIVE_EXPORT_SAVED"

        with conn.cursor() as cur:
            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type=event_type,
                actor_id=auth.user_id,
                actor_role=auth.role,
                detail={
                    "file_name": final_name,
                    "folder_id": folder_id or "source_folder",
                    "status": export_status,
                },
            )
        conn.commit()

        return envelope({
            "file_name": final_name,
            "folder_id": folder_id or "source_folder",
            "status": export_status,
            "message": "Export prepared. File upload requires Drive write scope.",
        })
    except Exception as e:
        logger.error("drive_export error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
