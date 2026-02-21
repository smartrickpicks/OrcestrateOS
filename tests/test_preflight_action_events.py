import asyncio
import importlib.util
import pathlib
import sys
import types


def _load_preflight_module():
    if "_preflight_routes_under_test" in sys.modules:
        return sys.modules["_preflight_routes_under_test"]

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

    try:
        import pydantic  # noqa: F401
    except ModuleNotFoundError:
        pydantic_mod = types.ModuleType("pydantic")

        class _BaseModel:
            def __init__(self, **kwargs):
                for k, v in kwargs.items():
                    setattr(self, k, v)

            def model_dump(self):
                return dict(self.__dict__)

            def dict(self):
                return dict(self.__dict__)

        def _field(default=None, default_factory=None, **kwargs):
            if default_factory is not None:
                return default_factory()
            return default

        pydantic_mod.BaseModel = _BaseModel
        pydantic_mod.Field = _field
        sys.modules["pydantic"] = pydantic_mod

    server_api = types.ModuleType("server.api_v25")
    server_api.envelope = lambda data: {
        "data": data,
        "meta": {"request_id": "req_test", "timestamp": "2026-01-01T00:00:00Z"},
    }
    server_api.error_envelope = lambda code, message, details=None: {
        "error": {"code": code, "message": message, "details": details}
    }
    sys.modules["server.api_v25"] = server_api

    server_auth = types.ModuleType("server.auth")

    class _AuthClass:
        EITHER = "either"

    server_auth.AuthClass = _AuthClass
    server_auth.require_auth = lambda *_args, **_kwargs: (lambda: None)
    server_auth.require_role = lambda *_args, **_kwargs: None
    server_auth.get_workspace_role = lambda *_args, **_kwargs: "admin"
    sys.modules["server.auth"] = server_auth

    server_flags = types.ModuleType("server.feature_flags")
    server_flags.is_preflight_enabled = lambda: True
    server_flags.require_preflight = lambda: None
    sys.modules["server.feature_flags"] = server_flags

    server_preflight_engine = types.ModuleType("server.preflight_engine")
    server_preflight_engine.run_preflight = lambda pages: {
        "gate_color": "GREEN",
        "gate_reasons": ["all_checks_passed"],
        "decision_trace": [],
    }
    server_preflight_engine.derive_cache_identity = lambda ws_id, file_url: "doc_derived_test"
    sys.modules["server.preflight_engine"] = server_preflight_engine

    server_db = types.ModuleType("server.db")
    server_db.get_conn = lambda: None
    server_db.put_conn = lambda conn: None
    sys.modules["server.db"] = server_db

    server_ulid = types.ModuleType("server.ulid")
    server_ulid.generate_id = lambda prefix="id_": prefix + "TEST"
    sys.modules["server.ulid"] = server_ulid

    preflight_path = pathlib.Path(__file__).resolve().parents[1] / "server" / "routes" / "preflight.py"
    spec = importlib.util.spec_from_file_location("_preflight_routes_under_test", preflight_path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    sys.modules["_preflight_routes_under_test"] = module
    return module


class _Auth:
    def __init__(self, user_id="usr_test", workspace_id=None, is_api_key=False):
        self.user_id = user_id
        self.workspace_id = workspace_id
        self.is_api_key = is_api_key


class _Request:
    def __init__(self, headers=None):
        self.headers = headers or {}


_preflight = _load_preflight_module()


def _run(coro):
    return asyncio.run(coro)


def test_preflight_action_appends_events_immutably_and_increments_count():
    _preflight._preflight_cache.clear()
    _preflight._preflight_cache["ws_1::doc_1"] = {
        "gate_color": "YELLOW",
        "gate_reasons": ["doc_mode_mixed"],
        "decision_trace": [{"rule": "doc_mode == MIXED", "result": "FAIL"}],
        "metrics": {"total_pages": 2},
    }

    auth = _Auth(user_id="usr_1")
    request = _Request(headers={"X-Workspace-Id": "ws_1"})

    first_payload = _preflight.PreflightActionRequest(doc_id="doc_1", action="generate_copy")
    first_resp = _run(_preflight.preflight_action(request, first_payload, auth=auth))
    assert first_resp.status_code == 200
    first_data = first_resp.content["data"]
    assert first_data["selected_action"] == "generate_copy"
    assert first_data["action_events_count"] == 1
    first_event = dict(first_data["latest_event"])

    second_payload = _preflight.PreflightActionRequest(doc_id="doc_1", action="escalate_ocr")
    second_resp = _run(_preflight.preflight_action(request, second_payload, auth=auth))
    assert second_resp.status_code == 200
    second_data = second_resp.content["data"]
    assert second_data["selected_action"] == "escalate_ocr"
    assert second_data["action_events_count"] == 2

    events = _preflight._preflight_cache["ws_1::doc_1"]["action_events"]
    assert events[0] == first_event
    assert events[0]["action"] == "generate_copy"
    assert events[1]["action"] == "escalate_ocr"
    assert events[0]["action_id"] != events[1]["action_id"]


def test_preflight_action_blocks_accept_risk_on_red_gate():
    _preflight._preflight_cache.clear()
    _preflight._preflight_cache["ws_1::doc_red"] = {
        "gate_color": "RED",
        "gate_reasons": ["replacement_char_ratio_exceeded"],
        "decision_trace": [{"rule": "replacement_char_ratio > 0.02", "result": "FAIL"}],
        "metrics": {"total_pages": 1},
    }

    auth = _Auth(user_id="usr_1")
    request = _Request(headers={"X-Workspace-Id": "ws_1"})
    payload = _preflight.PreflightActionRequest(doc_id="doc_red", action="accept_risk")

    resp = _run(_preflight.preflight_action(request, payload, auth=auth))
    assert resp.status_code == 400
    assert resp.content["error"]["code"] == "GATE_BLOCKED"

