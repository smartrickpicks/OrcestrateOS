import logging

from server.auth import get_workspace_role

logger = logging.getLogger(__name__)

ROLE_HIERARCHY = {"analyst": 0, "verifier": 1, "admin": 2, "architect": 3}


def resolve_effective_role(request, auth, ws_id):
    if auth.is_api_key:
        return "admin"

    sandbox_mode = request.headers.get("X-Sandbox-Mode", "").strip().lower()
    effective_role_header = request.headers.get("X-Effective-Role", "").strip().lower()

    if sandbox_mode == "true" and effective_role_header in ("analyst", "verifier", "admin"):
        db_role = get_workspace_role(auth.user_id, ws_id)
        capable_role = db_role or (auth.role if auth.role else None)
        if capable_role in ("admin", "architect"):
            return effective_role_header

    if auth.is_role_simulated and auth.effective_role:
        return auth.effective_role

    db_role = get_workspace_role(auth.user_id, ws_id)
    if db_role:
        return db_role
    if auth.user_id == "sandbox_user" and auth.role:
        return auth.role
    return "analyst"


def require_workspace_member(request, auth, ws_id):
    if auth.is_api_key:
        return "admin", None

    if auth.user_id == "sandbox_user":
        sandbox_mode = request.headers.get("X-Sandbox-Mode", "").strip().lower()
        if sandbox_mode == "true":
            effective_role = resolve_effective_role(request, auth, ws_id)
            return effective_role, None

    db_role = get_workspace_role(auth.user_id, ws_id)
    if db_role is None:
        from fastapi.responses import JSONResponse
        from server.api_v25 import error_envelope
        return None, JSONResponse(
            status_code=403,
            content=error_envelope("FORBIDDEN", "No role assigned in this workspace"),
        )

    effective_role = resolve_effective_role(request, auth, ws_id)
    return effective_role, None
