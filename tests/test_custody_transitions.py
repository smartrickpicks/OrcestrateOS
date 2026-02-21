import importlib.util
import json
import pathlib
import sys
import types


def _load_route_module(module_name, relative_path):
    saved = {}

    def _set_module(name, module):
        saved[name] = sys.modules.get(name)
        sys.modules[name] = module

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

        def patch(self, *args, **kwargs):
            return self._decorator(*args, **kwargs)

    def _depends(dep):
        return dep

    def _query(default=None, **kwargs):
        return default

    class _Request:
        def __init__(self):
            self.query_params = {}

    fastapi_mod.APIRouter = _APIRouter
    fastapi_mod.Depends = _depends
    fastapi_mod.Query = _query
    fastapi_mod.Request = _Request

    fastapi_responses = types.ModuleType("fastapi.responses")

    class _JSONResponse:
        def __init__(self, status_code=200, content=None):
            self.status_code = status_code
            self.content = content if content is not None else {}
            self.body = json.dumps(self.content).encode("utf-8")

    fastapi_responses.JSONResponse = _JSONResponse

    server_pkg = types.ModuleType("server")
    server_pkg.__path__ = []
    routes_pkg = types.ModuleType("server.routes")
    routes_pkg.__path__ = []

    server_db = types.ModuleType("server.db")
    server_db.get_conn = lambda: None
    server_db.put_conn = lambda _conn: None

    server_ulid = types.ModuleType("server.ulid")
    server_ulid.generate_id = lambda prefix="id_": prefix + "test"

    server_api = types.ModuleType("server.api_v25")
    server_api.envelope = lambda data: {"data": data}
    server_api.collection_envelope = lambda items, cursor=None, has_more=False, limit=50: {
        "data": items,
        "meta": {"cursor": cursor, "has_more": has_more, "limit": limit},
    }
    server_api.error_envelope = lambda code, message, details=None: {
        "error": {"code": code, "message": message, "details": details}
    }

    server_auth = types.ModuleType("server.auth")

    class _AuthClass:
        EITHER = "either"
        BEARER = "bearer"

    class _Role:
        ANALYST = "analyst"
        VERIFIER = "verifier"
        ADMIN = "admin"
        ARCHITECT = "architect"

    server_auth.AuthClass = _AuthClass
    server_auth.Role = _Role
    server_auth.require_auth = lambda *_args, **_kwargs: (lambda: None)
    server_auth.get_workspace_role = lambda *_args, **_kwargs: None

    server_audit = types.ModuleType("server.audit")
    server_audit.emit_audit_event = lambda *_args, **_kwargs: None

    server_role_scope = types.ModuleType("server.role_scope")
    server_role_scope.require_workspace_member = lambda *_args, **_kwargs: ("analyst", None)

    server_flags = types.ModuleType("server.feature_flags")
    server_flags.require_evidence_inspector = lambda: None

    _set_module("fastapi", fastapi_mod)
    _set_module("fastapi.responses", fastapi_responses)
    _set_module("server", server_pkg)
    _set_module("server.routes", routes_pkg)
    _set_module("server.db", server_db)
    _set_module("server.ulid", server_ulid)
    _set_module("server.api_v25", server_api)
    _set_module("server.auth", server_auth)
    _set_module("server.audit", server_audit)
    _set_module("server.role_scope", server_role_scope)
    _set_module("server.feature_flags", server_flags)

    route_path = pathlib.Path(__file__).resolve().parents[1] / relative_path
    spec = importlib.util.spec_from_file_location(module_name, route_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    try:
        spec.loader.exec_module(module)
    finally:
        for name, previous in saved.items():
            if previous is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = previous
    return module


patches = _load_route_module("_patches_under_test", "server/routes/patches.py")
rfis = _load_route_module("_rfis_under_test", "server/routes/rfis.py")
corrections = _load_route_module("_corrections_under_test", "server/routes/corrections.py")


class _Auth:
    def __init__(self, user_id, role):
        self.user_id = user_id
        self.role = role
        self.is_role_simulated = False
        self.actual_role = role
        self.effective_role = role


def _extract_set_fields(sql):
    if " SET " not in sql or " WHERE " not in sql:
        return []
    set_segment = sql.split(" SET ", 1)[1].split(" WHERE ", 1)[0]
    fields = []
    for assignment in set_segment.split(","):
        part = assignment.strip()
        if "=" not in part:
            continue
        left, right = part.split("=", 1)
        if "%s" in right:
            fields.append(left.strip())
    return fields


def _row_from_state(columns, state):
    return tuple(state.get(col) for col in columns)


class _PatchCursor:
    def __init__(self, state, columns):
        self.state = state
        self.columns = columns
        self.mode = None
        self.params = None
        self.sql = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params or ()
        if "FROM patches WHERE id = %s" in sql and sql.strip().startswith("SELECT"):
            self.mode = "select"
        elif sql.strip().startswith("UPDATE patches SET"):
            self.mode = "update"
        else:
            self.mode = "other"

    def fetchone(self):
        if self.mode == "select":
            return _row_from_state(self.columns, self.state)
        if self.mode == "update":
            patch_id = self.params[-2]
            provided_version = self.params[-1]
            if patch_id != self.state["id"] or provided_version != self.state["version"]:
                return None
            fields = _extract_set_fields(self.sql)
            for idx, field in enumerate(fields):
                self.state[field] = self.params[idx]
            self.state["version"] += 1
            return _row_from_state(self.columns, self.state)
        return None


class _PatchConn:
    def __init__(self, state, columns):
        self.cursor_obj = _PatchCursor(state, columns)

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        return None

    def rollback(self):
        return None


class _RfiCursor:
    def __init__(self, state, columns):
        self.state = state
        self.columns = columns
        self.mode = None
        self.params = None
        self.sql = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params or ()
        if "SELECT version, deleted_at, workspace_id, status, custody_status, custody_owner_id, custody_owner_role FROM rfis WHERE id = %s" in sql:
            self.mode = "select_meta"
        elif "SELECT author_id FROM rfis WHERE id = %s" in sql:
            self.mode = "select_author"
        elif sql.strip().startswith("UPDATE rfis SET"):
            self.mode = "update"
        else:
            self.mode = "other"

    def fetchone(self):
        if self.mode == "select_meta":
            return (
                self.state["version"],
                self.state.get("deleted_at"),
                self.state["workspace_id"],
                self.state["status"],
                self.state["custody_status"],
                self.state["custody_owner_id"],
                self.state["custody_owner_role"],
            )
        if self.mode == "select_author":
            return (self.state["author_id"],)
        if self.mode == "update":
            rfi_id = self.params[-2]
            provided_version = self.params[-1]
            if rfi_id != self.state["id"] or provided_version != self.state["version"]:
                return None
            fields = _extract_set_fields(self.sql)
            for idx, field in enumerate(fields):
                self.state[field] = self.params[idx]
            self.state["version"] += 1
            return _row_from_state(self.columns, self.state)
        return None


class _RfiConn:
    def __init__(self, state, columns):
        self.cursor_obj = _RfiCursor(state, columns)

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        return None

    def rollback(self):
        return None


class _CorrectionCursor:
    def __init__(self, state, columns):
        self.state = state
        self.columns = columns
        self.mode = None
        self.params = None
        self.sql = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False

    def execute(self, sql, params=None):
        self.sql = sql
        self.params = params or ()
        if "SELECT version, deleted_at, workspace_id, status FROM corrections WHERE id = %s" in sql:
            self.mode = "select_meta"
        elif sql.strip().startswith("UPDATE corrections SET"):
            self.mode = "update"
        else:
            self.mode = "other"

    def fetchone(self):
        if self.mode == "select_meta":
            return (
                self.state["version"],
                self.state.get("deleted_at"),
                self.state["workspace_id"],
                self.state["status"],
            )
        if self.mode == "update":
            correction_id = self.params[-2]
            provided_version = self.params[-1]
            if correction_id != self.state["id"] or provided_version != self.state["version"]:
                return None
            fields = _extract_set_fields(self.sql)
            for idx, field in enumerate(fields):
                self.state[field] = self.params[idx]
            self.state["version"] += 1
            return _row_from_state(self.columns, self.state)
        return None


class _CorrectionConn:
    def __init__(self, state, columns):
        self.cursor_obj = _CorrectionCursor(state, columns)

    def cursor(self):
        return self.cursor_obj

    def commit(self):
        return None

    def rollback(self):
        return None


def _assert_error(resp, expected_status, expected_code):
    assert getattr(resp, "status_code", None) == expected_status
    err = (resp.content or {}).get("error") or {}
    assert err.get("code") == expected_code


def _patch_common(monkeypatch, module, conn):
    monkeypatch.setattr(module, "get_conn", lambda: conn)
    monkeypatch.setattr(module, "put_conn", lambda _conn: None)
    monkeypatch.setattr(module, "emit_audit_event", lambda *_args, **_kwargs: None)


def _patch_role_check(monkeypatch, role_map):
    def _check_role(user_id, _workspace_id, min_role, _conn):
        role = role_map.get(user_id)
        if role is None:
            return None, "No role assigned in this workspace"
        if patches.ROLE_HIERARCHY.get(role, -1) < patches.ROLE_HIERARCHY.get(min_role, -1):
            return None, "Insufficient role: requires %s, you have %s" % (min_role, role)
        return role, None

    monkeypatch.setattr(patches, "_check_role", _check_role)


def _patch_base_state(status="Submitted", version=1):
    return {
        "id": "pat_1",
        "workspace_id": "ws_1",
        "batch_id": "bat_1",
        "record_id": "rec_1",
        "field_key": "Account_Name__c",
        "author_id": "usr_analyst",
        "status": status,
        "intent": "intent",
        "when_clause": None,
        "then_clause": None,
        "because_clause": "because",
        "evidence_pack_id": None,
        "submitted_at": None,
        "resolved_at": None,
        "file_name": None,
        "file_url": None,
        "before_value": "A",
        "after_value": "B",
        "history": [],
        "created_at": None,
        "updated_at": None,
        "deleted_at": None,
        "version": version,
        "metadata": {},
    }


def _rfi_base_state(custody_status="awaiting_verifier", version=1):
    return {
        "id": "rfi_1",
        "workspace_id": "ws_1",
        "patch_id": None,
        "author_id": "usr_analyst",
        "target_record_id": "rec_1",
        "target_field_key": "Account_Name__c",
        "question": "q",
        "response": None,
        "responder_id": None,
        "status": "open",
        "created_at": None,
        "updated_at": None,
        "deleted_at": None,
        "version": version,
        "metadata": {},
        "custody_status": custody_status,
        "custody_owner_id": "usr_verifier" if custody_status == "awaiting_verifier" else "usr_analyst",
        "custody_owner_role": "verifier" if custody_status == "awaiting_verifier" else "analyst",
        "batch_id": "bat_1",
    }


def _correction_base_state(status="pending_verifier", version=1):
    return {
        "id": "cor_1",
        "document_id": "doc_1",
        "workspace_id": "ws_1",
        "anchor_id": None,
        "rfi_id": None,
        "field_id": "fld_1",
        "field_key": "Account_Name__c",
        "original_value": "A",
        "corrected_value": "B",
        "correction_type": "non_trivial",
        "status": status,
        "decided_by": None,
        "decided_at": None,
        "created_by": "usr_analyst",
        "created_at": None,
        "updated_at": None,
        "deleted_at": None,
        "version": version,
        "metadata": {},
    }


def test_patch_transition_matrix_approve_reject_and_apply(monkeypatch):
    role_map = {"usr_verifier": "verifier", "usr_admin": "admin", "usr_analyst": "analyst"}
    _patch_role_check(monkeypatch, role_map)

    patch_state = _patch_base_state(status="Submitted", version=2)
    _patch_common(monkeypatch, patches, _PatchConn(patch_state, patches.PATCH_COLUMNS))
    verifier_auth = _Auth("usr_verifier", "verifier")
    admin_auth = _Auth("usr_admin", "admin")

    approved = patches.update_patch("pat_1", {"status": "Verifier_Approved", "version": 2}, verifier_auth)
    assert approved["data"]["status"] == "Verifier_Approved"
    assert approved["data"]["version"] == 3

    admin_approved = patches.update_patch("pat_1", {"status": "Admin_Approved", "version": 3}, admin_auth)
    assert admin_approved["data"]["status"] == "Admin_Approved"
    assert admin_approved["data"]["version"] == 4

    applied = patches.update_patch("pat_1", {"status": "Applied", "version": 4}, admin_auth)
    assert applied["data"]["status"] == "Applied"
    assert applied["data"]["version"] == 5

    reject_state = _patch_base_state(status="Submitted", version=7)
    _patch_common(monkeypatch, patches, _PatchConn(reject_state, patches.PATCH_COLUMNS))
    rejected = patches.update_patch("pat_1", {"status": "Rejected", "version": 7}, verifier_auth)
    assert rejected["data"]["status"] == "Rejected"
    assert rejected["data"]["version"] == 8


def test_patch_transition_errors_403_and_409(monkeypatch):
    role_map = {"usr_author": "verifier", "usr_verifier": "verifier", "usr_admin": "admin"}
    _patch_role_check(monkeypatch, role_map)

    self_blocked_state = _patch_base_state(status="Submitted", version=3)
    self_blocked_state["author_id"] = "usr_author"
    _patch_common(monkeypatch, patches, _PatchConn(self_blocked_state, patches.PATCH_COLUMNS))
    self_blocked = patches.update_patch("pat_1", {"status": "Verifier_Approved", "version": 3}, _Auth("usr_author", "verifier"))
    _assert_error(self_blocked, 403, "SELF_APPROVAL_BLOCKED")

    stale_state = _patch_base_state(status="Submitted", version=4)
    _patch_common(monkeypatch, patches, _PatchConn(stale_state, patches.PATCH_COLUMNS))
    stale = patches.update_patch("pat_1", {"status": "Verifier_Approved", "version": 1}, _Auth("usr_verifier", "verifier"))
    _assert_error(stale, 409, "STALE_VERSION")

    invalid_state = _patch_base_state(status="Submitted", version=5)
    _patch_common(monkeypatch, patches, _PatchConn(invalid_state, patches.PATCH_COLUMNS))
    invalid = patches.update_patch("pat_1", {"status": "Applied", "version": 5}, _Auth("usr_verifier", "verifier"))
    _assert_error(invalid, 409, "INVALID_TRANSITION")

    forbidden_state = _patch_base_state(status="Admin_Approved", version=6)
    _patch_common(monkeypatch, patches, _PatchConn(forbidden_state, patches.PATCH_COLUMNS))
    forbidden = patches.update_patch("pat_1", {"status": "Applied", "version": 6}, _Auth("usr_verifier", "verifier"))
    _assert_error(forbidden, 403, "FORBIDDEN")


def test_rfi_resolve_return_and_errors(monkeypatch):
    role_map = {"usr_analyst": "analyst", "usr_verifier": "verifier", "usr_admin": "admin"}
    monkeypatch.setattr(rfis, "get_workspace_role", lambda user_id, _ws: role_map.get(user_id))
    _patch_common(monkeypatch, rfis, _RfiConn(_rfi_base_state(version=1), rfis.RFI_COLUMNS))

    returned = rfis.update_rfi("rfi_1", {"custody_status": "returned_to_analyst", "version": 1}, _Auth("usr_verifier", "verifier"))
    assert returned["data"]["custody_status"] == "returned_to_analyst"
    assert returned["data"]["version"] == 2

    resubmitted = rfis.update_rfi("rfi_1", {"custody_status": "awaiting_verifier", "version": 2}, _Auth("usr_analyst", "analyst"))
    assert resubmitted["data"]["custody_status"] == "awaiting_verifier"
    assert resubmitted["data"]["version"] == 3

    resolved = rfis.update_rfi("rfi_1", {"custody_status": "resolved", "version": 3}, _Auth("usr_verifier", "verifier"))
    assert resolved["data"]["custody_status"] == "resolved"
    assert resolved["data"]["version"] == 4

    forbidden_state = _rfi_base_state(custody_status="awaiting_verifier", version=10)
    _patch_common(monkeypatch, rfis, _RfiConn(forbidden_state, rfis.RFI_COLUMNS))
    forbidden = rfis.update_rfi("rfi_1", {"custody_status": "resolved", "version": 10}, _Auth("usr_analyst", "analyst"))
    _assert_error(forbidden, 403, "ROLE_NOT_ALLOWED")

    invalid_state = _rfi_base_state(custody_status="awaiting_verifier", version=11)
    _patch_common(monkeypatch, rfis, _RfiConn(invalid_state, rfis.RFI_COLUMNS))
    invalid = rfis.update_rfi("rfi_1", {"custody_status": "open", "version": 11}, _Auth("usr_verifier", "verifier"))
    _assert_error(invalid, 409, "INVALID_TRANSITION")

    stale_state = _rfi_base_state(custody_status="awaiting_verifier", version=12)
    _patch_common(monkeypatch, rfis, _RfiConn(stale_state, rfis.RFI_COLUMNS))
    stale = rfis.update_rfi("rfi_1", {"custody_status": "resolved", "version": 4}, _Auth("usr_verifier", "verifier"))
    _assert_error(stale, 409, "STALE_VERSION")


def test_correction_approve_reject_and_errors(monkeypatch):
    role_map = {"usr_analyst": "analyst", "usr_verifier": "verifier", "usr_admin": "admin"}
    monkeypatch.setattr(corrections, "get_workspace_role", lambda user_id, _ws: role_map.get(user_id))
    _patch_common(monkeypatch, corrections, _CorrectionConn(_correction_base_state(status="pending_verifier", version=1), corrections.CORRECTION_COLUMNS))

    approved = corrections.update_correction("cor_1", {"status": "approved", "version": 1}, _Auth("usr_verifier", "verifier"))
    assert approved["data"]["status"] == "approved"
    assert approved["data"]["version"] == 2

    reject_state = _correction_base_state(status="pending_verifier", version=7)
    _patch_common(monkeypatch, corrections, _CorrectionConn(reject_state, corrections.CORRECTION_COLUMNS))
    rejected = corrections.update_correction("cor_1", {"status": "rejected", "version": 7}, _Auth("usr_admin", "admin"))
    assert rejected["data"]["status"] == "rejected"
    assert rejected["data"]["version"] == 8

    forbidden_state = _correction_base_state(status="pending_verifier", version=9)
    _patch_common(monkeypatch, corrections, _CorrectionConn(forbidden_state, corrections.CORRECTION_COLUMNS))
    forbidden = corrections.update_correction("cor_1", {"status": "approved", "version": 9}, _Auth("usr_analyst", "analyst"))
    _assert_error(forbidden, 403, "ROLE_NOT_ALLOWED")

    stale_state = _correction_base_state(status="pending_verifier", version=10)
    _patch_common(monkeypatch, corrections, _CorrectionConn(stale_state, corrections.CORRECTION_COLUMNS))
    stale = corrections.update_correction("cor_1", {"status": "approved", "version": 3}, _Auth("usr_verifier", "verifier"))
    _assert_error(stale, 409, "STALE_VERSION")

    invalid_state = _correction_base_state(status="approved", version=11)
    _patch_common(monkeypatch, corrections, _CorrectionConn(invalid_state, corrections.CORRECTION_COLUMNS))
    invalid = corrections.update_correction("cor_1", {"status": "rejected", "version": 11}, _Auth("usr_verifier", "verifier"))
    _assert_error(invalid, 409, "INVALID_TRANSITION")
