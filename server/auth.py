import hashlib
import logging
from enum import Enum
from typing import Optional

from fastapi import Request
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.api_v25 import error_envelope

logger = logging.getLogger(__name__)


class AuthClass(str, Enum):
    NONE = "none"
    BEARER = "bearer"
    API_KEY = "api_key"
    EITHER = "either"


class Role(str, Enum):
    ANALYST = "analyst"
    VERIFIER = "verifier"
    ADMIN = "admin"
    ARCHITECT = "architect"


ROLE_HIERARCHY = {
    Role.ANALYST: 0,
    Role.VERIFIER: 1,
    Role.ADMIN: 2,
    Role.ARCHITECT: 3,
}


class AuthResult:
    def __init__(self, user_id=None, email=None, display_name=None,
                 workspace_id=None, role=None, auth_type=None,
                 api_key_scopes=None):
        self.user_id = user_id
        self.email = email
        self.display_name = display_name
        self.workspace_id = workspace_id
        self.role = role
        self.auth_type = auth_type
        self.api_key_scopes = api_key_scopes or []

    @property
    def is_api_key(self):
        return self.auth_type == "api_key"


def _resolve_bearer(token):
    from server.jwt_utils import verify_jwt
    jwt_payload = verify_jwt(token)
    if jwt_payload:
        user_id = jwt_payload.get("sub") or jwt_payload.get("user_id")
        if user_id:
            conn = get_conn()
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT status FROM users WHERE id = %s", (user_id,))
                    row = cur.fetchone()
                    if row and row[0] == "inactive":
                        logger.info("JWT user %s is inactive, denying access", user_id)
                        return None
            finally:
                put_conn(conn)
        return AuthResult(
            user_id=user_id,
            email=jwt_payload.get("email"),
            display_name=jwt_payload.get("name"),
            workspace_id=jwt_payload.get("workspace_id"),
            role=jwt_payload.get("role"),
            auth_type="bearer",
        )

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, email, display_name, status FROM users WHERE id = %s",
                (token,),
            )
            row = cur.fetchone()
            if not row:
                cur.execute(
                    "SELECT id, email, display_name, status FROM users WHERE email = %s",
                    (token,),
                )
                row = cur.fetchone()
            if row:
                if len(row) > 3 and row[3] == "inactive":
                    return None
                return AuthResult(
                    user_id=row[0],
                    email=row[1],
                    display_name=row[2],
                    auth_type="bearer",
                )
        return None
    finally:
        put_conn(conn)


def _resolve_api_key(key_value):
    key_hash = hashlib.sha256(key_value.encode("utf-8")).hexdigest()
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT key_id, workspace_id, scopes, created_by, revoked_at, expires_at
                   FROM api_keys
                   WHERE key_hash = %s""",
                (key_hash,),
            )
            row = cur.fetchone()
            if not row:
                return None
            key_id, workspace_id, scopes, created_by, revoked_at, expires_at = row
            if revoked_at is not None:
                return None
            if expires_at is not None:
                from datetime import datetime, timezone
                if expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
                    return None

            cur.execute(
                "UPDATE api_keys SET last_used_at = NOW() WHERE key_id = %s",
                (key_id,),
            )
        conn.commit()
        return AuthResult(
            user_id=created_by,
            workspace_id=workspace_id,
            auth_type="api_key",
            api_key_scopes=scopes if isinstance(scopes, list) else [],
        )
    except Exception as e:
        logger.error("API key resolution error: %s", e)
        conn.rollback()
        return None
    finally:
        put_conn(conn)


def resolve_auth(request: Request):
    bearer = request.headers.get("Authorization", "")
    api_key = request.headers.get("X-API-Key", "")

    if bearer.startswith("Bearer "):
        token = bearer[7:].strip()
        if token:
            return _resolve_bearer(token), "bearer"

    if api_key:
        result = _resolve_api_key(api_key)
        if result:
            return result, "api_key"

    return None, None


def get_workspace_role(user_id, workspace_id):
    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT role FROM user_workspace_roles WHERE user_id = %s AND workspace_id = %s",
                (user_id, workspace_id),
            )
            row = cur.fetchone()
            if row:
                return row[0]
        return None
    finally:
        put_conn(conn)


def has_minimum_role(user_role, required_role):
    if user_role is None:
        return False
    user_level = ROLE_HIERARCHY.get(user_role, ROLE_HIERARCHY.get(Role(user_role), -1))
    required_level = ROLE_HIERARCHY.get(required_role, ROLE_HIERARCHY.get(Role(required_role), -1))
    return user_level >= required_level


def require_auth(auth_class: AuthClass):
    def dependency(request: Request):
        if auth_class == AuthClass.NONE:
            return None

        auth_result, auth_type = resolve_auth(request)

        if auth_result is None:
            return JSONResponse(
                status_code=401,
                content=error_envelope("UNAUTHORIZED", "Authentication required"),
            )

        if auth_class == AuthClass.BEARER and auth_type != "bearer":
            return JSONResponse(
                status_code=401,
                content=error_envelope("UNAUTHORIZED", "Bearer token required for this endpoint"),
            )

        if auth_class == AuthClass.API_KEY and auth_type != "api_key":
            return JSONResponse(
                status_code=401,
                content=error_envelope("UNAUTHORIZED", "API key required for this endpoint"),
            )

        request.state.auth = auth_result
        return auth_result

    return dependency


def require_role(workspace_id, auth_result, min_role):
    if auth_result.is_api_key:
        return None

    role = get_workspace_role(auth_result.user_id, workspace_id)
    if role is None:
        return JSONResponse(
            status_code=403,
            content=error_envelope("FORBIDDEN", "No role assigned in this workspace"),
        )
    auth_result.role = role
    auth_result.workspace_id = workspace_id

    if not has_minimum_role(role, min_role):
        return JSONResponse(
            status_code=403,
            content=error_envelope(
                "FORBIDDEN",
                "Insufficient role: requires %s, you have %s" % (min_role, role),
            ),
        )
    return None
