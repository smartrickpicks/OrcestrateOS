import asyncio
import base64
import importlib.util
import pathlib
import re
import sys
import types
from datetime import datetime, timezone


def _load_drive_module():
    if "_drive_under_test" in sys.modules:
        return sys.modules["_drive_under_test"]

    fastapi_mod = types.ModuleType("fastapi")

    class _APIRouter:
        def __init__(self, *args, **kwargs):
            pass

        def _decorator(self, *args, **kwargs):
            return lambda fn: fn

        def get(self, *args, **kwargs):
            return self._decorator(*args, **kwargs)

        def post(self, *args, **kwargs):
            return self._decorator(*args, **kwargs)

        def delete(self, *args, **kwargs):
            return self._decorator(*args, **kwargs)

        def put(self, *args, **kwargs):
            return self._decorator(*args, **kwargs)

        def patch(self, *args, **kwargs):
            return self._decorator(*args, **kwargs)

    def _depends(dep):
        return dep

    def _query(default=None, **kwargs):
        return default

    class _Request:
        pass

    fastapi_mod.APIRouter = _APIRouter
    fastapi_mod.Depends = _depends
    fastapi_mod.Query = _query
    fastapi_mod.Request = _Request
    sys.modules["fastapi"] = fastapi_mod

    fastapi_responses = types.ModuleType("fastapi.responses")

    class _JSONResponse:
        def __init__(self, status_code=200, content=None):
            self.status_code = status_code
            self.content = content

    fastapi_responses.JSONResponse = _JSONResponse
    sys.modules["fastapi.responses"] = fastapi_responses

    server_db = types.ModuleType("server.db")
    server_db.get_conn = lambda: None
    server_db.put_conn = lambda conn: None
    sys.modules["server.db"] = server_db

    server_ulid = types.ModuleType("server.ulid")
    server_ulid.generate_id = lambda prefix="id_": prefix + "TEST"
    sys.modules["server.ulid"] = server_ulid

    server_api = types.ModuleType("server.api_v25")
    server_api.envelope = lambda data: {"data": data}
    server_api.collection_envelope = lambda items, **kwargs: {"data": items, "meta": kwargs}
    server_api.error_envelope = lambda code, message, details=None: {
        "error": {"code": code, "message": message, "details": details}
    }
    sys.modules["server.api_v25"] = server_api

    server_auth = types.ModuleType("server.auth")

    class _AuthClass:
        BEARER = "bearer"
        EITHER = "either"

    class _Role:
        ANALYST = "analyst"

    server_auth.AuthClass = _AuthClass
    server_auth.Role = _Role
    server_auth.require_auth = lambda *_args, **_kwargs: (lambda: None)
    server_auth.require_role = lambda *_args, **_kwargs: None
    server_auth.get_workspace_role = lambda *_args, **_kwargs: "admin"
    sys.modules["server.auth"] = server_auth

    server_audit = types.ModuleType("server.audit")
    server_audit.emit_audit_event = lambda *_args, **_kwargs: None
    sys.modules["server.audit"] = server_audit

    server_custody = types.ModuleType("server.custody_canary")
    server_custody.trigger_session_handoff = lambda *_args, **_kwargs: None
    sys.modules["server.custody_canary"] = server_custody

    drive_path = pathlib.Path(__file__).resolve().parents[1] / "server" / "routes" / "drive.py"
    spec = importlib.util.spec_from_file_location("_drive_under_test", drive_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    sys.modules["_drive_under_test"] = module
    return module


_drive = _load_drive_module()


def test_normalize_export_status_aliases_and_default():
    assert _drive._normalize_export_status("in_progress") == "IN_PROGRESS_ANALYST"
    assert _drive._normalize_export_status("verifier done") == "VERIFIER_DONE"
    assert _drive._normalize_export_status("ADMIN_FINAL") == "ADMIN_FINAL"
    assert _drive._normalize_export_status("unexpected-value") == "IN_PROGRESS_ANALYST"


def test_build_export_filename_is_canonical():
    fixed_now = datetime(2026, 2, 18, 16, 45, tzinfo=timezone.utc)
    actual = _drive._build_export_filename(
        dataset_or_batch="batch_001.xlsx",
        status="verifier_done",
        workspace_id="ws demo",
        now_utc=fixed_now,
    )
    assert actual == "batch_001__VERIFIER_DONE__2026-02-18_16-45__ws_demo.xlsx"


def test_drive_save_normalizes_status_and_audit_metadata(monkeypatch):
    class _Auth:
        user_id = "usr_123"
        role = "analyst"
        display_name = "Analyst Example"
        email = "analyst@example.com"

    class _Req:
        def __init__(self, body):
            self._body = body

        async def json(self):
            return self._body

    class _Cursor:
        def __init__(self, conn):
            self._conn = conn
            self._fetchone = None

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def execute(self, sql, params=None):
            self._conn.queries.append((sql, params))
            if "SELECT drive_folder_id FROM user_workspace_roles" in sql:
                self._fetchone = None
            else:
                self._fetchone = None

        def fetchone(self):
            return self._fetchone

    class _Conn:
        def __init__(self):
            self.queries = []
            self.commits = 0
            self.rollbacks = 0

        def cursor(self):
            return _Cursor(self)

        def commit(self):
            self.commits += 1

        def rollback(self):
            self.rollbacks += 1

    class _CreateCall:
        def __init__(self, body):
            self._body = body

        def execute(self):
            return {
                "id": "drv_file_1",
                "name": self._body.get("name"),
                "webViewLink": "https://drive.google.com/file/d/drv_file_1/view",
                "size": "12",
            }

    class _FilesApi:
        def create(self, body=None, media_body=None, fields=None, supportsAllDrives=None):
            return _CreateCall(body or {})

    class _DriveService:
        def files(self):
            return _FilesApi()

    fake_conn = _Conn()
    audit_events = []

    monkeypatch.setattr(_drive, "get_conn", lambda: fake_conn)
    monkeypatch.setattr(_drive, "put_conn", lambda _conn: None)
    monkeypatch.setattr(
        _drive,
        "_get_workspace_connection",
        lambda _ws_id, _conn: ("conn_1", None, None, None, "token", None, None, "active"),
    )
    monkeypatch.setattr(_drive, "_refresh_token_if_needed", lambda _row, _conn: "token")
    monkeypatch.setattr(_drive, "_get_drive_service", lambda _token: _DriveService())
    monkeypatch.setattr(
        _drive,
        "_get_drive_settings",
        lambda _ws_id, _conn: {"root_folder_id": None, "verifier_folder_id": None, "admin_folder_id": None},
    )
    monkeypatch.setattr(_drive, "require_role", lambda *_args, **_kwargs: None)
    monkeypatch.setattr(_drive, "_bootstrap_folder", lambda *_args, **_kwargs: "folder_verifier")

    google_http_mod = types.ModuleType("googleapiclient.http")

    class _MediaInMemoryUpload:
        def __init__(self, data, mimetype=None, resumable=False):
            self.data = data
            self.mimetype = mimetype
            self.resumable = resumable

    google_http_mod.MediaInMemoryUpload = _MediaInMemoryUpload
    monkeypatch.setitem(sys.modules, "googleapiclient.http", google_http_mod)

    def _capture_audit(_cur, **kwargs):
        audit_events.append(kwargs)
        return "aud_1"

    monkeypatch.setattr(_drive, "emit_audit_event", _capture_audit)

    payload = {
        "batch_id": "Batch 001",
        "status": "in progress",
        "note": "handoff",
        "file_content_base64": base64.b64encode(b"test-bytes").decode("ascii"),
    }

    resp = asyncio.run(_drive.drive_save("ws_demo", _Req(payload), _Auth()))
    assert "data" in resp
    data = resp["data"]
    assert data["status"] == "IN_PROGRESS_ANALYST"
    assert re.match(
        r"^Batch_001__IN_PROGRESS_ANALYST__\d{4}-\d{2}-\d{2}_\d{2}-\d{2}__ws_demo\.xlsx$",
        data["file_name"],
    )
    assert data["file_id"] == "drv_file_1"

    assert len(audit_events) == 1
    detail = audit_events[0]["detail"]
    assert detail["status"] == "IN_PROGRESS_ANALYST"
    assert detail["status_raw"] == "in progress"
    assert detail["batch_id"] == "Batch 001"
