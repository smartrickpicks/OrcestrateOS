import base64
import hashlib
import io
import json
import logging
import os
import re
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.ulid import generate_id
from server.api_v25 import envelope, collection_envelope, error_envelope
from server.auth import AuthClass, require_auth, require_role, Role
from server.audit import emit_audit_event
from server.custody_canary import trigger_session_handoff

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

DRIVE_ROOT_FOLDER_ID = os.environ.get("DRIVE_ROOT_FOLDER_ID", "")

EXPORT_STATUS_ENUM = {
    "IN_PROGRESS_ANALYST": "IN_PROGRESS_ANALYST",
    "ANALYST_DONE": "ANALYST_DONE",
    "VERIFIER_DONE": "VERIFIER_DONE",
    "ADMIN_FINAL": "ADMIN_FINAL",
    "REJECTED": "REJECTED",
}
EXPORT_STATUS_ALIASES = {
    "IN_PROGRESS": "IN_PROGRESS_ANALYST",
    "INPROGRESS": "IN_PROGRESS_ANALYST",
    "IN_PROGRESS_ANALYST": "IN_PROGRESS_ANALYST",
    "ANALYST_DONE": "ANALYST_DONE",
    "VERIFIER_DONE": "VERIFIER_DONE",
    "ADMIN_FINAL": "ADMIN_FINAL",
    "REJECTED": "REJECTED",
}

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


class DriveImportFailure(Exception):
    def __init__(self, code, message, status_code=500, details=None, preflight=None):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details
        self.preflight = preflight


def _row_to_dict(row, columns):
    d = {}
    for i, col in enumerate(columns):
        val = row[i]
        if isinstance(val, datetime):
            d[col] = val.isoformat()
        else:
            d[col] = val
    return d


def _normalize_export_status(raw_status):
    status_raw = (raw_status or "").strip()
    if not status_raw:
        return EXPORT_STATUS_ENUM["IN_PROGRESS_ANALYST"]
    normalized = re.sub(r"[^A-Za-z0-9_]+", "_", status_raw).upper()
    normalized = re.sub(r"_+", "_", normalized).strip("_")
    return EXPORT_STATUS_ALIASES.get(normalized, EXPORT_STATUS_ENUM["IN_PROGRESS_ANALYST"])


def _sanitize_filename_part(value, fallback):
    part = (value or "").strip()
    part = re.sub(r"\.(xlsx|xls|csv)$", "", part, flags=re.IGNORECASE)
    part = re.sub(r"[^A-Za-z0-9_.-]+", "_", part)
    part = re.sub(r"_+", "_", part).strip("_.")
    return part[:64] if part else fallback


def _build_export_filename(dataset_or_batch, status, workspace_id, now_utc=None):
    ts = (now_utc or datetime.now(timezone.utc)).strftime("%Y-%m-%d_%H-%M")
    seed = _sanitize_filename_part(dataset_or_batch, "dataset")
    ws_part = _sanitize_filename_part(workspace_id, "workspace")
    normalized_status = _normalize_export_status(status)
    return "%s__%s__%s__%s.xlsx" % (seed, normalized_status, ts, ws_part)


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


def _supported_import_mime(mime):
    if not mime:
        return True
    if mime == "application/vnd.google-apps.spreadsheet":
        return True
    return mime in (
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "application/vnd.ms-excel",
        "text/csv",
        "text/plain",
    )


def _build_drive_import_preflight(
    file_id,
    file_name,
    ordinal=None,
    total=None,
    file_meta=None,
    retry_reused=False,
    error=None,
):
    file_id = (file_id or "").strip()
    file_name = (file_name or "").strip()
    mime_type = (file_meta or {}).get("mimeType")
    modified_time = (file_meta or {}).get("modifiedTime")
    md5 = (file_meta or {}).get("md5Checksum")
    size_raw = (file_meta or {}).get("size")
    size_bytes = None
    try:
        size_bytes = int(size_raw) if size_raw is not None else None
    except Exception:
        size_bytes = None

    payload = {
        "file_id": file_id,
        "file_name": file_name,
        "ordinal": ordinal,
        "total": total,
        "mime_type": mime_type,
        "size_bytes": size_bytes,
        "modified_time": modified_time,
        "md5": md5,
        "retry_reused": bool(retry_reused),
        "checks": {
            "file_id_present": bool(file_id),
            "drive_metadata_available": file_meta is not None,
            "size_within_limit": (size_bytes is None) or (size_bytes <= MAX_IMPORT_SIZE_BYTES),
            "mime_supported": _supported_import_mime(mime_type),
        },
        "error": error or None,
    }
    stable = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    payload["fingerprint"] = hashlib.sha256(stable.encode("utf-8")).hexdigest()
    return payload


def _new_batch_progress(total):
    return {
        "total": int(total or 0),
        "processed": 0,
        "remaining": int(total or 0),
        "succeeded": 0,
        "failed": 0,
        "skipped": 0,
        "state": "running",
    }


def _increment_batch_progress(progress, status):
    progress["processed"] += 1
    if status == "succeeded":
        progress["succeeded"] += 1
    elif status == "failed":
        progress["failed"] += 1
    else:
        progress["skipped"] += 1
    progress["remaining"] = max(progress["total"] - progress["processed"], 0)
    return dict(progress)


def _finalize_batch_progress(progress):
    if progress["failed"] == 0 and progress["succeeded"] == progress["total"]:
        progress["state"] = "completed"
    elif progress["failed"] > 0 and progress["succeeded"] > 0:
        progress["state"] = "partial_failure"
    elif progress["failed"] > 0 and progress["succeeded"] == 0:
        progress["state"] = "failed"
    elif progress["processed"] == progress["total"] and progress["skipped"] == progress["total"]:
        progress["state"] = "skipped"
    else:
        progress["state"] = "completed_with_skips"
    return progress


def _status_message_for_progress(progress):
    return (
        "Processed %(processed)d/%(total)d files: %(succeeded)d succeeded, %(failed)d failed, %(skipped)d skipped."
        % progress
    )


def _status_code_for_progress(progress):
    return 200 if progress["failed"] == 0 else 207


def _execute_batch_import(file_items, import_one, continue_on_error=True):
    total = len(file_items or [])
    progress = _new_batch_progress(total)
    results = []
    seen_file_ids = set()
    stop_at = None

    for idx, raw_item in enumerate(file_items or []):
        item = raw_item if isinstance(raw_item, dict) else {}
        file_id = (item.get("file_id") or "").strip()
        file_name = (item.get("file_name") or "").strip()
        ordinal = idx + 1
        entry = {
            "index": idx,
            "file_id": file_id,
            "file_name": file_name,
        }

        if not file_id:
            pf = _build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name,
                ordinal=ordinal,
                total=total,
                error={"code": "VALIDATION_ERROR", "message": "file_id is required"},
            )
            entry["status"] = "failed"
            entry["status_message"] = "Skipped: file_id is required."
            entry["preflight"] = pf
            entry["error"] = {"code": "VALIDATION_ERROR", "message": "file_id is required"}
            entry["progress"] = _increment_batch_progress(progress, "failed")
            results.append(entry)
            if not continue_on_error:
                stop_at = idx + 1
                break
            continue

        if file_id in seen_file_ids:
            pf = _build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name,
                ordinal=ordinal,
                total=total,
                retry_reused=True,
                error={"code": "DUPLICATE_IN_REQUEST", "message": "duplicate file_id in request"},
            )
            entry["status"] = "skipped"
            entry["status_message"] = "Skipped duplicate file in request for retry safety."
            entry["preflight"] = pf
            entry["error"] = {"code": "DUPLICATE_IN_REQUEST", "message": "duplicate file_id in request"}
            entry["progress"] = _increment_batch_progress(progress, "skipped")
            results.append(entry)
            continue

        seen_file_ids.add(file_id)
        try:
            imported = import_one(file_id=file_id, file_name=file_name, ordinal=ordinal, total=total)
            entry["status"] = "succeeded"
            entry["status_message"] = imported.get("status_message", "Imported file successfully.")
            entry["preflight"] = imported.get(
                "preflight",
                _build_drive_import_preflight(file_id=file_id, file_name=file_name, ordinal=ordinal, total=total),
            )
            entry["result"] = imported
            entry["progress"] = _increment_batch_progress(progress, "succeeded")
            results.append(entry)
        except DriveImportFailure as e:
            entry["status"] = "failed"
            entry["status_message"] = "Import failed: %s" % e.message
            entry["preflight"] = e.preflight or _build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name,
                ordinal=ordinal,
                total=total,
                error={"code": e.code, "message": e.message},
            )
            error_obj = {"code": e.code, "message": e.message}
            if e.details is not None:
                error_obj["details"] = e.details
            entry["error"] = error_obj
            entry["progress"] = _increment_batch_progress(progress, "failed")
            results.append(entry)
            if not continue_on_error:
                stop_at = idx + 1
                break
        except Exception as e:
            entry["status"] = "failed"
            entry["status_message"] = "Import failed due to an unexpected internal error."
            entry["preflight"] = _build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name,
                ordinal=ordinal,
                total=total,
                error={"code": "INTERNAL", "message": str(e)},
            )
            entry["error"] = {"code": "INTERNAL", "message": str(e)}
            entry["progress"] = _increment_batch_progress(progress, "failed")
            results.append(entry)
            if not continue_on_error:
                stop_at = idx + 1
                break

    if stop_at is not None and stop_at < total:
        for idx in range(stop_at, total):
            item = file_items[idx] if isinstance(file_items[idx], dict) else {}
            file_id = (item.get("file_id") or "").strip()
            file_name = (item.get("file_name") or "").strip()
            pf = _build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name,
                ordinal=idx + 1,
                total=total,
                error={"code": "HALTED", "message": "batch stopped after previous failure"},
            )
            entry = {
                "index": idx,
                "file_id": file_id,
                "file_name": file_name,
                "status": "skipped",
                "status_message": "Not attempted because batch was halted after a failure.",
                "preflight": pf,
                "error": {"code": "HALTED", "message": "batch stopped after previous failure"},
            }
            entry["progress"] = _increment_batch_progress(progress, "skipped")
            results.append(entry)

    _finalize_batch_progress(progress)
    payload = {
        "progress_state_cleared": True,
        "progress": progress,
        "status_message": _status_message_for_progress(progress),
        "items": results,
    }
    return payload, _status_code_for_progress(progress)


def _download_drive_file_bytes(service, file_id, file_name, ordinal=None, total=None):
    try:
        file_meta = service.files().get(
            fileId=file_id,
            fields="id, name, mimeType, size, modifiedTime, md5Checksum, parents",
            supportsAllDrives=True,
        ).execute()
    except Exception as e:
        raise DriveImportFailure(
            code="DRIVE_IMPORT_FETCH_FAILED",
            message="Unable to fetch Google Drive metadata.",
            status_code=502,
            details={"file_id": file_id, "reason": str(e)},
            preflight=_build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name,
                ordinal=ordinal,
                total=total,
                error={"code": "DRIVE_IMPORT_FETCH_FAILED", "message": str(e)},
            ),
        )

    file_size = int(file_meta.get("size", 0) or 0)
    if file_size > MAX_IMPORT_SIZE_BYTES:
        raise DriveImportFailure(
            code="FILE_TOO_LARGE",
            message="File exceeds 50MB limit (%d bytes)" % file_size,
            status_code=413,
            details={"size_bytes": file_size, "max_bytes": MAX_IMPORT_SIZE_BYTES},
            preflight=_build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name or file_meta.get("name"),
                ordinal=ordinal,
                total=total,
                file_meta=file_meta,
                error={"code": "FILE_TOO_LARGE", "message": "size exceeds limit"},
            ),
        )

    mime = file_meta.get("mimeType", "")
    google_export_mimes = {
        "application/vnd.google-apps.spreadsheet": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xlsx",
        ),
    }

    from googleapiclient.http import MediaIoBaseDownload
    if mime in google_export_mimes:
        export_mime, ext = google_export_mimes[mime]
        request_dl = service.files().export_media(fileId=file_id, mimeType=export_mime)
    else:
        ext = None
        request_dl = service.files().get_media(fileId=file_id, supportsAllDrives=True)

    buf = io.BytesIO()
    downloader = MediaIoBaseDownload(buf, request_dl)
    done = False
    while not done:
        _, done = downloader.next_chunk()

    file_bytes = buf.getvalue()
    raw_name = file_meta.get("name", "file")
    if ext:
        name_base = raw_name.rsplit(".", 1)[0] if "." in raw_name else raw_name
        download_name = name_base + ext
    else:
        download_name = raw_name

    return file_meta, file_bytes, file_size, download_name


def _import_drive_file_record(
    ws_id,
    auth,
    conn,
    service,
    file_id,
    file_name="",
    ordinal=None,
    total=None,
):
    if not file_id:
        raise DriveImportFailure(
            code="VALIDATION_ERROR",
            message="file_id is required",
            status_code=400,
            preflight=_build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name,
                ordinal=ordinal,
                total=total,
                error={"code": "VALIDATION_ERROR", "message": "file_id is required"},
            ),
        )

    file_meta, file_bytes, file_size, download_name = _download_drive_file_bytes(
        service=service,
        file_id=file_id,
        file_name=file_name,
        ordinal=ordinal,
        total=total,
    )
    file_b64 = base64.b64encode(file_bytes).decode("ascii")
    modified_time = file_meta.get("modifiedTime")
    drive_md5 = file_meta.get("md5Checksum")
    drive_id_val = file_meta.get("parents", [None])[0] if file_meta.get("parents") else None

    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT %s FROM drive_import_provenance
                   WHERE workspace_id = %s
                     AND source_file_id = %s
                     AND drive_modified_time = %s
                     AND COALESCE(drive_md5, '') = COALESCE(%s, '')
                   ORDER BY version_number DESC
                   LIMIT 1""" % PROV_SELECT,
                (ws_id, file_id, modified_time, drive_md5),
            )
            retry_row = cur.fetchone()
            if retry_row:
                retry_result = _row_to_dict(retry_row, PROV_COLUMNS)
                retry_result["is_refresh"] = bool(retry_result.get("supersedes_id"))
                retry_result["retry_reused"] = True
                retry_result["file_content_base64"] = file_b64
                retry_result["file_name"] = download_name
                retry_result["preflight"] = _build_drive_import_preflight(
                    file_id=file_id,
                    file_name=file_name or file_meta.get("name"),
                    ordinal=ordinal,
                    total=total,
                    file_meta=file_meta,
                    retry_reused=True,
                )
                retry_result["status_message"] = "Already imported this file revision; reused existing result."
                emit_audit_event(
                    cur,
                    workspace_id=ws_id,
                    event_type="DRIVE_FILE_IMPORT_REUSED",
                    actor_id=auth.user_id,
                    actor_role=auth.role,
                    resource_type="drive_import_provenance",
                    resource_id=retry_result["id"],
                    detail={
                        "source_file_id": file_id,
                        "file_name": file_meta.get("name"),
                        "version_number": retry_result.get("version_number"),
                        "retry_reused": True,
                    },
                )
                conn.commit()
                return retry_result

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
            cur.execute(
                """INSERT INTO drive_import_provenance
                   (id, workspace_id, source_file_id, source_file_name,
                    source_mime_type, source_size_bytes, drive_id,
                    drive_modified_time, drive_md5,
                    version_number, supersedes_id, imported_by)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                   RETURNING """ + PROV_SELECT,
                (
                    prov_id,
                    ws_id,
                    file_id,
                    file_meta.get("name"),
                    file_meta.get("mimeType"),
                    file_size,
                    drive_id_val,
                    modified_time,
                    drive_md5,
                    new_version,
                    supersedes_id,
                    auth.user_id,
                ),
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
    except Exception as e:
        conn.rollback()
        raise DriveImportFailure(
            code="INTERNAL",
            message="Failed to record Drive import provenance.",
            status_code=500,
            details={"file_id": file_id, "reason": str(e)},
            preflight=_build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name or file_meta.get("name"),
                ordinal=ordinal,
                total=total,
                file_meta=file_meta,
                error={"code": "INTERNAL", "message": str(e)},
            ),
        )

    try:
        trigger_session_handoff(
            workspace_id=ws_id,
            actor_id=auth.user_id,
            trigger="drive_import",
            source_type="drive",
            source_ref=file_id,
            environment=None,
            metadata={
                "path": "drive_import",
                "provenance_id": prov_row[0],
                "file_name": file_meta.get("name"),
                "version_number": new_version,
                "is_refresh": is_refresh,
            },
        )
    except Exception as e:
        logger.warning("custody session handoff trigger failed (drive_import): %s", e)

    result = _row_to_dict(prov_row, PROV_COLUMNS)
    result["is_refresh"] = is_refresh
    result["retry_reused"] = False
    result["file_content_base64"] = file_b64
    result["file_name"] = download_name
    result["preflight"] = _build_drive_import_preflight(
        file_id=file_id,
        file_name=file_name or file_meta.get("name"),
        ordinal=ordinal,
        total=total,
        file_meta=file_meta,
        retry_reused=False,
    )
    result["status_message"] = "Imported file successfully."
    return result


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


def _build_redirect_uri():
    dev_domain = os.environ.get("REPLIT_DEV_DOMAIN", "")
    if dev_domain:
        return "https://%s/drive-callback.html" % dev_domain
    repl_slug = os.environ.get("REPL_SLUG", "")
    repl_owner = os.environ.get("REPL_OWNER", "")
    if repl_slug and repl_owner:
        return "https://%s.%s.repl.co/drive-callback.html" % (repl_slug, repl_owner)
    return ""


@router.get("/workspaces/{ws_id}/drive/status")
def drive_status(ws_id: str, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    redirect_uri_expected = _build_redirect_uri()

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return envelope({
            "connected": False,
            "has_token": False,
            "expires_at": None,
            "scopes": DRIVE_SCOPES,
            "redirect_uri_expected": redirect_uri_expected,
            "drive_email": None,
            "failure_reason": "missing_client_id_or_secret",
            "connection": None,
        })

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT id, workspace_id, connected_by, drive_email,
                          access_token, refresh_token, token_expiry,
                          status, connected_at, updated_at, metadata
                   FROM drive_connections
                   WHERE workspace_id = %s
                   ORDER BY updated_at DESC LIMIT 1""",
                (ws_id,),
            )
            conn_row = cur.fetchone()

        if not conn_row:
            return envelope({
                "connected": False,
                "has_token": False,
                "expires_at": None,
                "scopes": DRIVE_SCOPES,
                "redirect_uri_expected": redirect_uri_expected,
                "drive_email": None,
                "failure_reason": "token_not_found",
                "connection": None,
            })

        status = conn_row[7]
        access_token = conn_row[4]
        token_expiry = conn_row[6]
        has_token = bool(access_token)
        expires_at_iso = token_expiry.isoformat() if token_expiry else None

        connection_info = {
            "id": conn_row[0],
            "connected_by": conn_row[2],
            "connected_at": conn_row[8].isoformat() if conn_row[8] else None,
            "status": status,
        }

        if status != "active":
            return envelope({
                "connected": False,
                "has_token": has_token,
                "expires_at": expires_at_iso,
                "scopes": DRIVE_SCOPES,
                "redirect_uri_expected": redirect_uri_expected,
                "drive_email": conn_row[3],
                "failure_reason": "connection_revoked",
                "connection": connection_info,
            })

        failure_reason = None
        if token_expiry and token_expiry.replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
            refreshed_token = _refresh_token_if_needed(conn_row, conn)
            if refreshed_token == access_token:
                failure_reason = "token_expired"
            else:
                with conn.cursor() as cur:
                    cur.execute(
                        "SELECT token_expiry FROM drive_connections WHERE id = %s",
                        (conn_row[0],),
                    )
                    refreshed_row = cur.fetchone()
                    if refreshed_row and refreshed_row[0]:
                        expires_at_iso = refreshed_row[0].isoformat()
                        if refreshed_row[0].replace(tzinfo=timezone.utc) <= datetime.now(timezone.utc):
                            failure_reason = "refresh_failed"

        return envelope({
            "connected": failure_reason is None,
            "has_token": has_token,
            "expires_at": expires_at_iso,
            "scopes": DRIVE_SCOPES,
            "redirect_uri_expected": redirect_uri_expected,
            "drive_email": conn_row[3],
            "failure_reason": failure_reason,
            "connection": connection_info,
        })
    except Exception as e:
        logger.error("drive_status error: %s", e)
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.get("/workspaces/{ws_id}/drive/settings")
def drive_settings_get(ws_id: str, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ANALYST)
    if role_err:
        return role_err

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT workspace_id, root_folder_id, verifier_folder_id,
                          admin_folder_id, updated_at, updated_by
                   FROM workspace_drive_settings
                   WHERE workspace_id = %s""",
                (ws_id,),
            )
            row = cur.fetchone()

        if not row:
            return envelope({
                "workspace_id": ws_id,
                "root_folder_id": None,
                "verifier_folder_id": None,
                "admin_folder_id": None,
                "updated_at": None,
                "updated_by": None,
            })

        return envelope({
            "workspace_id": row[0],
            "root_folder_id": row[1],
            "verifier_folder_id": row[2],
            "admin_folder_id": row[3],
            "updated_at": row[4].isoformat() if row[4] else None,
            "updated_by": row[5],
        })
    except Exception as e:
        logger.error("drive_settings_get error: %s", e)
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.put("/workspaces/{ws_id}/drive/settings")
async def drive_settings_put(ws_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_err = require_role(ws_id, auth, Role.ADMIN)
    if role_err:
        return role_err

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid JSON body"),
        )

    root_folder_id = body.get("root_folder_id")
    verifier_folder_id = body.get("verifier_folder_id")
    admin_folder_id = body.get("admin_folder_id")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO workspace_drive_settings
                   (workspace_id, root_folder_id, verifier_folder_id, admin_folder_id, updated_by)
                   VALUES (%s, %s, %s, %s, %s)
                   ON CONFLICT (workspace_id) DO UPDATE SET
                       root_folder_id = EXCLUDED.root_folder_id,
                       verifier_folder_id = EXCLUDED.verifier_folder_id,
                       admin_folder_id = EXCLUDED.admin_folder_id,
                       updated_at = NOW(),
                       updated_by = EXCLUDED.updated_by
                   RETURNING workspace_id, root_folder_id, verifier_folder_id,
                             admin_folder_id, updated_at, updated_by""",
                (ws_id, root_folder_id, verifier_folder_id, admin_folder_id, auth.user_id),
            )
            row = cur.fetchone()

            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="DRIVE_SETTINGS_UPDATED",
                actor_id=auth.user_id,
                actor_role=auth.role,
                resource_type="workspace_drive_settings",
                resource_id=ws_id,
                detail={
                    "root_folder_id": root_folder_id,
                    "verifier_folder_id": verifier_folder_id,
                    "admin_folder_id": admin_folder_id,
                },
            )
        conn.commit()

        return envelope({
            "workspace_id": row[0],
            "root_folder_id": row[1],
            "verifier_folder_id": row[2],
            "admin_folder_id": row[3],
            "updated_at": row[4].isoformat() if row[4] else None,
            "updated_by": row[5],
        })
    except Exception as e:
        logger.error("drive_settings_put error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


def _get_drive_settings(ws_id, db_conn):
    with db_conn.cursor() as cur:
        cur.execute(
            """SELECT root_folder_id, verifier_folder_id, admin_folder_id
               FROM workspace_drive_settings
               WHERE workspace_id = %s""",
            (ws_id,),
        )
        row = cur.fetchone()
    if row:
        return {
            "root_folder_id": row[0],
            "verifier_folder_id": row[1],
            "admin_folder_id": row[2],
        }
    return {"root_folder_id": None, "verifier_folder_id": None, "admin_folder_id": None}


def _resolve_target_folder(role, settings):
    if role in ("analyst",):
        folder = settings.get("verifier_folder_id")
    elif role in ("verifier",):
        folder = settings.get("admin_folder_id")
    elif role in ("admin", "architect"):
        folder = settings.get("admin_folder_id")
    else:
        folder = None
    if folder:
        return folder
    if settings.get("root_folder_id"):
        return settings["root_folder_id"]
    if DRIVE_ROOT_FOLDER_ID:
        return DRIVE_ROOT_FOLDER_ID
    return None


def _bootstrap_folder(service, folder_label, parent_folder_id, ws_id, settings_key, db_conn):
    file_metadata = {
        "name": folder_label,
        "mimeType": "application/vnd.google-apps.folder",
    }
    if parent_folder_id:
        file_metadata["parents"] = [parent_folder_id]

    created = service.files().create(
        body=file_metadata,
        fields="id",
        supportsAllDrives=True,
    ).execute()
    new_folder_id = created["id"]

    with db_conn.cursor() as cur:
        cur.execute(
            """INSERT INTO workspace_drive_settings (workspace_id, %s)
               VALUES (%%s, %%s)
               ON CONFLICT (workspace_id) DO UPDATE SET
                   %s = EXCLUDED.%s,
                   updated_at = NOW()""" % (settings_key, settings_key, settings_key),
            (ws_id, new_folder_id),
        )
    db_conn.commit()
    return new_folder_id


@router.post("/workspaces/{ws_id}/drive/save")
async def drive_save(ws_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
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

    batch_id = body.get("batch_id", "").strip()
    save_status_raw = body.get("status", EXPORT_STATUS_ENUM["IN_PROGRESS_ANALYST"])
    save_status = _normalize_export_status(save_status_raw)
    note = body.get("note", "").strip()
    file_content_b64 = body.get("file_content_base64", "")

    if not batch_id:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "batch_id is required"),
        )
    if not file_content_b64:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "file_content_base64 is required"),
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

        settings = _get_drive_settings(ws_id, conn)
        role = auth.role or "analyst"

        member_folder = None
        with conn.cursor() as cur:
            cur.execute(
                "SELECT drive_folder_id FROM user_workspace_roles WHERE user_id = %s AND workspace_id = %s AND drive_folder_id IS NOT NULL",
                (auth.user_id, ws_id)
            )
            row = cur.fetchone()
            if row and row[0]:
                member_folder = row[0]

        if member_folder:
            target_folder = member_folder
        else:
            target_folder = _resolve_target_folder(role, settings)

        if not target_folder:
            root_id = settings.get("root_folder_id") or DRIVE_ROOT_FOLDER_ID or None
            if role in ("analyst",) and not settings.get("verifier_folder_id"):
                target_folder = _bootstrap_folder(
                    service, "Verifier", root_id, ws_id, "verifier_folder_id", conn,
                )
                settings["verifier_folder_id"] = target_folder
            elif role in ("verifier", "admin", "architect") and not settings.get("admin_folder_id"):
                target_folder = _bootstrap_folder(
                    service, "Admin", root_id, ws_id, "admin_folder_id", conn,
                )
                settings["admin_folder_id"] = target_folder

        file_name = _build_export_filename(batch_id, save_status, ws_id)

        file_bytes = base64.b64decode(file_content_b64)

        from googleapiclient.http import MediaInMemoryUpload
        media = MediaInMemoryUpload(
            file_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resumable=False,
        )

        file_metadata = {
            "name": file_name,
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        }
        if target_folder:
            file_metadata["parents"] = [target_folder]

        created = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink, size",
            supportsAllDrives=True,
        ).execute()

        drive_file_id = created.get("id", "")
        web_view_link = created.get("webViewLink", "")

        export_id = generate_id("dxh_")
        with conn.cursor() as cur:
            cur.execute(
                """INSERT INTO drive_export_history
                   (id, workspace_id, batch_id, file_name, drive_file_id,
                    folder_id, web_view_link, status, actor_id, actor_role,
                    note, size_bytes)
                   VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)""",
                (export_id, ws_id, batch_id, file_name, drive_file_id,
                 target_folder, web_view_link, save_status, auth.user_id,
                 role, note, len(file_bytes)),
            )

            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type="DRIVE_SAVE_COMPLETED",
                actor_id=auth.user_id,
                actor_role=role,
                resource_type="drive_export_history",
                resource_id=export_id,
                batch_id=batch_id,
                detail={
                    "file_name": file_name,
                    "folder_id": target_folder,
                    "status": save_status,
                    "status_raw": save_status_raw,
                    "batch_id": batch_id,
                    "drive_file_id": drive_file_id,
                    "size_bytes": len(file_bytes),
                    "note": note,
                },
            )
        conn.commit()

        return envelope({
            "ok": True,
            "file_id": drive_file_id,
            "file_name": file_name,
            "folder_id": target_folder,
            "webViewLink": web_view_link,
            "status": save_status,
        })
    except Exception as e:
        logger.error("drive_save error: %s", e)
        conn.rollback()
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

        q_parts = []
        if parent:
            q_parts.append("'%s' in parents" % parent)
        elif DRIVE_ROOT_FOLDER_ID:
            q_parts.append("'%s' in parents" % DRIVE_ROOT_FOLDER_ID)
        else:
            q_parts.append("'root' in parents")

        q_parts.append("trashed = false")
        q_parts.append(
            "(mimeType = 'application/vnd.google-apps.folder'"
            " or mimeType = 'application/vnd.google-apps.spreadsheet'"
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
        err_str = str(e)
        if "accessNotConfigured" in err_str or "has not been used in project" in err_str:
            return JSONResponse(
                status_code=503,
                content=error_envelope(
                    "DRIVE_API_NOT_ENABLED",
                    "The Google Drive API is not enabled in the Google Cloud project. "
                    "Please enable it at https://console.developers.google.com/apis/api/drive.googleapis.com/overview "
                    "and wait a few minutes before retrying.",
                ),
            )
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", err_str))
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

    file_id = (body.get("file_id") or "").strip()
    file_name = (body.get("file_name") or "").strip()

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
        result = _import_drive_file_record(
            ws_id=ws_id,
            auth=auth,
            conn=conn,
            service=service,
            file_id=file_id,
            file_name=file_name,
            ordinal=1,
            total=1,
        )
        status_code = 200 if result.get("retry_reused") else 201
        return JSONResponse(status_code=status_code, content=envelope(result))
    except DriveImportFailure as e:
        return JSONResponse(
            status_code=e.status_code,
            content=error_envelope(e.code, e.message, details=e.details),
        )
    except Exception as e:
        logger.error("drive_import error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)


@router.post("/workspaces/{ws_id}/drive/import-batch")
async def drive_import_batch(ws_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
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

    files = body.get("files")
    continue_on_error = body.get("continue_on_error", True)
    if not isinstance(continue_on_error, bool):
        continue_on_error = True

    if not isinstance(files, list) or len(files) == 0:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "files must be a non-empty array"),
        )

    if len(files) > 200:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "files exceeds maximum batch size (200)"),
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

        def _import_one(file_id, file_name, ordinal, total):
            return _import_drive_file_record(
                ws_id=ws_id,
                auth=auth,
                conn=conn,
                service=service,
                file_id=file_id,
                file_name=file_name,
                ordinal=ordinal,
                total=total,
            )

        payload, status_code = _execute_batch_import(
            file_items=files,
            import_one=_import_one,
            continue_on_error=continue_on_error,
        )
        return JSONResponse(status_code=status_code, content=envelope(payload))
    except Exception as e:
        logger.error("drive_import_batch error: %s", e)
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
    export_status_raw = body.get("status", EXPORT_STATUS_ENUM["IN_PROGRESS_ANALYST"])
    export_status = _normalize_export_status(export_status_raw)
    file_content_b64 = body.get("file_content_base64", "")

    if not file_name:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "file_name is required"),
        )
    if not file_content_b64:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "file_content_base64 is required"),
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

        final_name = file_name if file_name.endswith('.xlsx') else file_name + '.xlsx'

        file_bytes = base64.b64decode(file_content_b64)

        from googleapiclient.http import MediaInMemoryUpload
        media = MediaInMemoryUpload(
            file_bytes,
            mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            resumable=False,
        )

        file_metadata = {"name": final_name, "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"}
        if folder_id:
            file_metadata["parents"] = [folder_id]

        created = service.files().create(
            body=file_metadata,
            media_body=media,
            fields="id, name, webViewLink, size",
            supportsAllDrives=True,
        ).execute()

        drive_file_id = created.get("id", "")
        drive_link = created.get("webViewLink", "")

        final_states = ("ADMIN_FINAL", "VERIFIER_DONE", "REJECTED")
        event_type = "DRIVE_EXPORT_FINALIZED" if export_status in final_states else "DRIVE_EXPORT_SAVED"

        with conn.cursor() as cur:
            emit_audit_event(
                cur,
                workspace_id=ws_id,
                event_type=event_type,
                actor_id=auth.user_id,
                actor_role=auth.role,
                detail={
                    "file_name": final_name,
                    "folder_id": folder_id or "root",
                    "status": export_status,
                    "status_raw": export_status_raw,
                    "drive_file_id": drive_file_id,
                    "size_bytes": len(file_bytes),
                },
            )
        conn.commit()

        return envelope({
            "file_name": final_name,
            "drive_file_id": drive_file_id,
            "web_view_link": drive_link,
            "folder_id": folder_id or "root",
            "status": export_status,
            "size_bytes": len(file_bytes),
        })
    except Exception as e:
        logger.error("drive_export error: %s", e)
        conn.rollback()
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL", str(e)))
    finally:
        put_conn(conn)
