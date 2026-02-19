import importlib.util
import pathlib
import sys
import types


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
DriveImportFailure = _drive.DriveImportFailure
_build_drive_import_preflight = _drive._build_drive_import_preflight
_execute_batch_import = _drive._execute_batch_import


def test_drive_import_preflight_is_deterministic():
    meta = {
        "mimeType": "application/vnd.google-apps.spreadsheet",
        "size": "1024",
        "modifiedTime": "2026-02-18T00:00:00Z",
        "md5Checksum": "abc123",
    }
    one = _build_drive_import_preflight(
        file_id="drive_file_1",
        file_name="Contracts.xlsx",
        ordinal=1,
        total=3,
        file_meta=meta,
    )
    two = _build_drive_import_preflight(
        file_id="drive_file_1",
        file_name="Contracts.xlsx",
        ordinal=1,
        total=3,
        file_meta=meta,
    )

    assert one == two
    assert len(one["fingerprint"]) == 64
    assert one["checks"]["file_id_present"] is True
    assert one["checks"]["size_within_limit"] is True


def test_execute_batch_import_handles_mixed_success():
    def importer(file_id, file_name, ordinal, total):
        if file_id == "bad":
            raise DriveImportFailure(
                code="DRIVE_IMPORT_FETCH_FAILED",
                message="missing in Drive",
                status_code=404,
                preflight=_build_drive_import_preflight(
                    file_id=file_id,
                    file_name=file_name,
                    ordinal=ordinal,
                    total=total,
                    error={"code": "DRIVE_IMPORT_FETCH_FAILED", "message": "missing in Drive"},
                ),
            )
        return {
            "id": "drv_" + file_id,
            "status_message": "Imported " + file_name,
            "preflight": _build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name,
                ordinal=ordinal,
                total=total,
            ),
        }

    payload, status_code = _execute_batch_import(
        file_items=[
            {"file_id": "good_1", "file_name": "A.xlsx"},
            {"file_id": "bad", "file_name": "B.xlsx"},
            {"file_id": "good_2", "file_name": "C.xlsx"},
        ],
        import_one=importer,
        continue_on_error=True,
    )

    assert status_code == 207
    assert payload["progress_state_cleared"] is True
    assert payload["progress"]["total"] == 3
    assert payload["progress"]["processed"] == 3
    assert payload["progress"]["succeeded"] == 2
    assert payload["progress"]["failed"] == 1
    assert payload["progress"]["state"] == "partial_failure"
    assert payload["items"][0]["status"] == "succeeded"
    assert payload["items"][1]["status"] == "failed"
    assert payload["items"][1]["error"]["code"] == "DRIVE_IMPORT_FETCH_FAILED"
    assert payload["items"][2]["status"] == "succeeded"


def test_execute_batch_import_is_retry_safe_for_duplicate_ids():
    calls = []

    def importer(file_id, file_name, ordinal, total):
        calls.append((file_id, ordinal))
        return {
            "id": "drv_" + file_id,
            "status_message": "Imported " + file_name,
            "preflight": _build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name,
                ordinal=ordinal,
                total=total,
            ),
        }

    payload, status_code = _execute_batch_import(
        file_items=[
            {"file_id": "dup_1", "file_name": "A.xlsx"},
            {"file_id": "dup_1", "file_name": "A copy.xlsx"},
            {"file_id": "uniq_1", "file_name": "B.xlsx"},
        ],
        import_one=importer,
        continue_on_error=True,
    )

    assert status_code == 200
    assert calls == [("dup_1", 1), ("uniq_1", 3)]
    assert payload["progress"]["succeeded"] == 2
    assert payload["progress"]["skipped"] == 1
    assert payload["items"][1]["status"] == "skipped"
    assert payload["items"][1]["error"]["code"] == "DUPLICATE_IN_REQUEST"


def test_execute_batch_import_fail_fast_marks_remaining_as_halted():
    def importer(file_id, file_name, ordinal, total):
        if file_id == "bad":
            raise DriveImportFailure(
                code="FILE_TOO_LARGE",
                message="too large",
                status_code=413,
            )
        return {
            "id": "drv_" + file_id,
            "status_message": "Imported " + file_name,
            "preflight": _build_drive_import_preflight(
                file_id=file_id,
                file_name=file_name,
                ordinal=ordinal,
                total=total,
            ),
        }

    payload, status_code = _execute_batch_import(
        file_items=[
            {"file_id": "good_1", "file_name": "A.xlsx"},
            {"file_id": "bad", "file_name": "B.xlsx"},
            {"file_id": "good_2", "file_name": "C.xlsx"},
        ],
        import_one=importer,
        continue_on_error=False,
    )

    assert status_code == 207
    assert payload["progress"]["succeeded"] == 1
    assert payload["progress"]["failed"] == 1
    assert payload["progress"]["skipped"] == 1
    assert payload["items"][2]["status"] == "skipped"
    assert payload["items"][2]["error"]["code"] == "HALTED"
