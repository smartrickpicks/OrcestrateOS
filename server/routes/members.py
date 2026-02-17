import logging

from fastapi import APIRouter, Request, Depends
from fastapi.responses import JSONResponse

from server.db import get_conn, put_conn
from server.api_v25 import envelope, error_envelope
from server.auth import AuthClass, require_auth, require_role, Role
from server.ulid import generate_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2.5", tags=["members"])


@router.get("/workspaces/{ws_id}/members")
async def list_members(ws_id: str, request: Request, auth=Depends(require_auth(AuthClass.EITHER))):
    if isinstance(auth, JSONResponse):
        return auth

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """SELECT u.id, u.email, u.display_name, u.avatar_url, u.status,
                          uwr.role, u.created_at, u.updated_at
                   FROM users u
                   JOIN user_workspace_roles uwr ON u.id = uwr.user_id
                   WHERE uwr.workspace_id = %s
                   ORDER BY u.display_name ASC""",
                (ws_id,),
            )
            rows = cur.fetchall()

        members = []
        for row in rows:
            members.append({
                "id": row[0],
                "email": row[1],
                "display_name": row[2],
                "avatar_url": row[3],
                "status": row[4] or "active",
                "role": row[5],
                "created_at": row[6].isoformat() if row[6] else None,
                "updated_at": row[7].isoformat() if row[7] else None,
            })

        return JSONResponse(status_code=200, content=envelope(members))
    finally:
        put_conn(conn)


@router.post("/workspaces/{ws_id}/members")
async def create_member(ws_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    role_check = require_role(ws_id, auth, Role.ADMIN)
    if role_check:
        return role_check

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "Invalid JSON"))

    email = (body.get("email") or "").strip().lower()
    display_name = (body.get("display_name") or "").strip()
    role = (body.get("role") or "analyst").strip().lower()
    status = (body.get("status") or "active").strip().lower()

    if not email:
        return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "Email is required"))

    if role not in ("analyst", "verifier", "admin", "architect"):
        return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "Invalid role"))

    if status not in ("active", "inactive"):
        return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "Invalid status"))

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE LOWER(email) = %s", (email,))
            existing = cur.fetchone()

            if existing:
                user_id = existing[0]
                cur.execute(
                    "UPDATE users SET display_name = %s, status = %s, updated_at = NOW() WHERE id = %s",
                    (display_name, status, user_id),
                )
            else:
                user_id = generate_id("usr_")
                cur.execute(
                    "INSERT INTO users (id, email, display_name, status) VALUES (%s, %s, %s, %s)",
                    (user_id, email, display_name, status),
                )

            cur.execute(
                """INSERT INTO user_workspace_roles (user_id, workspace_id, role)
                   VALUES (%s, %s, %s)
                   ON CONFLICT (user_id, workspace_id) DO UPDATE SET role = EXCLUDED.role""",
                (user_id, ws_id, role),
            )

        conn.commit()

        return JSONResponse(
            status_code=201,
            content=envelope({
                "id": user_id,
                "email": email,
                "display_name": display_name,
                "role": role,
                "status": status,
                "workspace_id": ws_id,
            }),
        )
    except Exception as e:
        conn.rollback()
        logger.error("Create member error: %s", e)
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL_ERROR", "Failed to create member"))
    finally:
        put_conn(conn)


@router.patch("/members/{user_id}")
async def update_member(user_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "Invalid JSON"))

    workspace_id = body.get("workspace_id", "")
    if not workspace_id:
        return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "workspace_id required"))

    role_check = require_role(workspace_id, auth, Role.ADMIN)
    if role_check:
        return role_check

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id, email, display_name, status FROM users WHERE id = %s", (user_id,))
            user_row = cur.fetchone()
            if not user_row:
                return JSONResponse(status_code=404, content=error_envelope("NOT_FOUND", "User not found"))

            display_name = body.get("display_name", user_row[2])
            status = body.get("status", user_row[3])
            email = body.get("email", user_row[1])
            role = body.get("role")

            if status and status not in ("active", "inactive"):
                return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "Invalid status"))

            cur.execute(
                """UPDATE users SET display_name = %s, email = %s, status = %s, updated_at = NOW()
                   WHERE id = %s""",
                (display_name, email, status, user_id),
            )

            if role:
                if role not in ("analyst", "verifier", "admin", "architect"):
                    return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "Invalid role"))
                cur.execute(
                    """INSERT INTO user_workspace_roles (user_id, workspace_id, role)
                       VALUES (%s, %s, %s)
                       ON CONFLICT (user_id, workspace_id) DO UPDATE SET role = EXCLUDED.role""",
                    (user_id, workspace_id, role),
                )

        conn.commit()

        return JSONResponse(
            status_code=200,
            content=envelope({
                "id": user_id,
                "email": email,
                "display_name": display_name,
                "status": status,
                "role": role,
                "workspace_id": workspace_id,
            }),
        )
    except Exception as e:
        conn.rollback()
        logger.error("Update member error: %s", e)
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL_ERROR", "Failed to update member"))
    finally:
        put_conn(conn)


@router.get("/members/{user_id}/drive-folder")
async def get_member_drive_folder(user_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    workspace_id = request.query_params.get("workspace_id", "")
    if not workspace_id:
        return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "workspace_id required"))

    role_check = require_role(workspace_id, auth, Role.ANALYST)
    if role_check:
        return role_check

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT drive_folder_id, drive_folder_updated_at FROM user_workspace_roles WHERE user_id = %s AND workspace_id = %s",
                (user_id, workspace_id),
            )
            row = cur.fetchone()

        if not row:
            return JSONResponse(status_code=404, content=error_envelope("NOT_FOUND", "Member not found in workspace"))

        return JSONResponse(status_code=200, content=envelope({
            "user_id": user_id,
            "workspace_id": workspace_id,
            "drive_folder_id": row[0],
            "drive_folder_updated_at": row[1].isoformat() if row[1] else None,
        }))
    except Exception as e:
        logger.error("Get member drive folder error: %s", e)
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL_ERROR", "Failed to get drive folder"))
    finally:
        put_conn(conn)


@router.put("/members/{user_id}/drive-folder")
async def update_member_drive_folder(user_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "Invalid JSON"))

    workspace_id = body.get("workspace_id", "")
    if not workspace_id:
        return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "workspace_id required"))

    role_check = require_role(workspace_id, auth, Role.ADMIN)
    if role_check:
        return role_check

    drive_folder_id = body.get("drive_folder_id", "")

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                """UPDATE user_workspace_roles
                   SET drive_folder_id = %s, drive_folder_updated_at = NOW()
                   WHERE user_id = %s AND workspace_id = %s
                   RETURNING user_id, workspace_id, drive_folder_id, drive_folder_updated_at""",
                (drive_folder_id or None, user_id, workspace_id),
            )
            row = cur.fetchone()

        if not row:
            conn.rollback()
            return JSONResponse(status_code=404, content=error_envelope("NOT_FOUND", "Member not found in workspace"))

        conn.commit()
        return JSONResponse(status_code=200, content=envelope({
            "user_id": row[0],
            "workspace_id": row[1],
            "drive_folder_id": row[2],
            "drive_folder_updated_at": row[3].isoformat() if row[3] else None,
        }))
    except Exception as e:
        conn.rollback()
        logger.error("Update member drive folder error: %s", e)
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL_ERROR", "Failed to update drive folder"))
    finally:
        put_conn(conn)


@router.delete("/members/{user_id}")
async def delete_member(user_id: str, request: Request, auth=Depends(require_auth(AuthClass.BEARER))):
    if isinstance(auth, JSONResponse):
        return auth

    workspace_id = request.query_params.get("workspace_id", "")
    if not workspace_id:
        return JSONResponse(status_code=400, content=error_envelope("VALIDATION_ERROR", "workspace_id required"))

    role_check = require_role(workspace_id, auth, Role.ADMIN)
    if role_check:
        return role_check

    conn = get_conn()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET status = 'inactive', updated_at = NOW() WHERE id = %s",
                (user_id,),
            )
            cur.execute(
                "DELETE FROM user_workspace_roles WHERE user_id = %s AND workspace_id = %s",
                (user_id, workspace_id),
            )
        conn.commit()
        return JSONResponse(status_code=200, content=envelope({"id": user_id, "deleted": True}))
    except Exception as e:
        conn.rollback()
        logger.error("Delete member error: %s", e)
        return JSONResponse(status_code=500, content=error_envelope("INTERNAL_ERROR", "Failed to remove member"))
    finally:
        put_conn(conn)
