"""
Preflight API routes for Orchestrate OS.

POST /api/preflight/run     - Run preflight analysis on a document (URL)
POST /api/preflight/upload  - Run preflight on uploaded PDF (base64, internal/Test Lab)
GET  /api/preflight/{doc_id} - Read cached preflight result
POST /api/preflight/action  - Accept Risk / Escalate OCR (internal)

All require:
  - v2.5 Either auth (Bearer or API key)
  - Feature flag PREFLIGHT_GATE_SYNC or alias enabled
  - ADMIN role (sandbox stage)
  - Workspace isolation
"""
import hashlib
import logging
from datetime import datetime, timezone
from urllib.parse import urlparse, unquote

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import JSONResponse

from server.api_v25 import envelope, error_envelope
from server.auth import AuthClass, require_auth, require_role, get_workspace_role
from server.feature_flags import is_preflight_enabled, require_preflight
from server.preflight_engine import run_preflight, derive_cache_identity
from server.db import get_conn, put_conn
from server.ulid import generate_id

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/preflight", tags=["preflight"])

_preflight_cache = {}


def _resolve_workspace(request, auth, body=None):
    """Resolve workspace_id: auth-bound first, then X-Workspace-Id fallback."""
    ws_id = getattr(auth, "workspace_id", None)
    if not ws_id:
        ws_id = request.headers.get("X-Workspace-Id", "").strip()
    if not ws_id and body and isinstance(body, dict):
        ws_id = body.get("workspace_id", "")
    if not ws_id:
        return None, JSONResponse(
            status_code=422,
            content=error_envelope("MISSING_WORKSPACE", "Workspace ID is required"),
        )
    return ws_id, None


def _require_admin_sandbox(auth, workspace_id):
    """Admin-only sandbox gate. Returns error response or None."""
    if auth.is_api_key:
        return None
    if getattr(auth, 'user_id', None) == 'sandbox_user':
        return None
    role = get_workspace_role(auth.user_id, workspace_id)
    if role != "admin" and role != "architect":
        return JSONResponse(
            status_code=403,
            content=error_envelope("FORBIDDEN", "Preflight is in admin sandbox mode."),
        )
    return None


def _cache_key(workspace_id, doc_id):
    return "%s::%s" % (workspace_id, doc_id)


def _extract_pages_from_pdf(pdf_bytes):
    """Extract page data from PDF bytes using PyMuPDF. Returns (pages_data, error_response)."""
    import fitz
    try:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_data = []
        for i in range(len(doc)):
            page = doc[i]
            text = page.get_text("text")
            page_rect = page.rect
            page_area = page_rect.width * page_rect.height if page_rect else 1
            images = page.get_images(full=True)
            image_area = 0
            for img in images:
                try:
                    xref = img[0]
                    img_rects = page.get_image_rects(xref)
                    for r in img_rects:
                        image_area += r.width * r.height
                except Exception:
                    pass
            image_ratio = min(image_area / page_area, 1.0) if page_area > 0 else 0.0
            pages_data.append({
                "page": i + 1,
                "text": text,
                "char_count": len(text),
                "image_coverage_ratio": round(image_ratio, 4),
                "page_width": round(page_rect.width, 2) if page_rect else 0,
                "page_height": round(page_rect.height, 2) if page_rect else 0,
            })
        doc.close()
        return pages_data, None
    except Exception as e:
        return None, JSONResponse(
            status_code=422,
            content=error_envelope("EXTRACTION_ERROR", "PDF analysis failed: %s" % str(e)),
        )


def _build_preflight_result(pages_data, doc_id, ws_id, file_url):
    """Run preflight engine and build cacheable result dict."""
    result = run_preflight(pages_data)
    result["doc_id"] = doc_id
    result["workspace_id"] = ws_id
    result["file_url"] = file_url
    result["timestamp"] = datetime.now(timezone.utc).isoformat()
    result["materialized"] = False

    for pd_item in pages_data:
        for pr in result.get("page_classifications", []):
            if pr["page"] == pd_item["page"]:
                pr["page_width"] = pd_item.get("page_width", 0)
                pr["page_height"] = pd_item.get("page_height", 0)

    ck = _cache_key(ws_id, doc_id)
    _preflight_cache[ck] = result
    return result


@router.post("/run")
async def preflight_run(
    request: Request,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    """Run preflight analysis on a document."""
    if isinstance(auth, JSONResponse):
        return auth

    flag_check = require_preflight()
    if flag_check:
        return flag_check

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid JSON body"),
        )

    ws_id, ws_err = _resolve_workspace(request, auth, body)
    if ws_err:
        return ws_err

    admin_err = _require_admin_sandbox(auth, ws_id)
    if admin_err:
        return admin_err

    file_url = body.get("file_url", "").strip()
    doc_id = body.get("doc_id", "").strip()

    if not file_url:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "file_url is required"),
        )

    if not doc_id:
        doc_id = derive_cache_identity(ws_id, file_url)

    from server.pdf_proxy import is_host_allowed, is_private_ip, MAX_SIZE_BYTES
    import httpx

    try:
        decoded_url = unquote(file_url)
        parsed = urlparse(decoded_url)
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid file_url format"),
        )

    if parsed.scheme not in ("http", "https"):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Only HTTP/HTTPS URLs allowed"),
        )

    hostname = parsed.hostname
    if not hostname:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Missing hostname in file_url"),
        )

    if not is_host_allowed(hostname):
        return JSONResponse(
            status_code=403,
            content=error_envelope("FORBIDDEN", "Host not in allowlist: %s" % hostname),
        )

    if is_private_ip(hostname):
        return JSONResponse(
            status_code=403,
            content=error_envelope("FORBIDDEN", "Private/reserved IPs are blocked"),
        )

    async with httpx.AsyncClient(timeout=30.0, follow_redirects=False) as client:
        try:
            resp = await client.get(decoded_url)
            if resp.status_code in (301, 302, 303, 307, 308):
                redirect_url = resp.headers.get("location")
                if redirect_url:
                    redirect_parsed = urlparse(redirect_url)
                    redirect_host = redirect_parsed.hostname
                    if not redirect_host or not is_host_allowed(redirect_host) or is_private_ip(redirect_host):
                        return JSONResponse(
                            status_code=403,
                            content=error_envelope("FORBIDDEN", "Redirect to non-allowlisted host blocked"),
                        )
                    resp = await client.get(redirect_url)
            resp.raise_for_status()
            if len(resp.content) > MAX_SIZE_BYTES:
                return JSONResponse(
                    status_code=413,
                    content=error_envelope("FILE_TOO_LARGE", "File exceeds size limit"),
                )
        except httpx.TimeoutException:
            return JSONResponse(
                status_code=504,
                content=error_envelope("UPSTREAM_TIMEOUT", "PDF fetch timed out"),
            )
        except httpx.HTTPStatusError as e:
            return JSONResponse(
                status_code=e.response.status_code,
                content=error_envelope("UPSTREAM_ERROR", "Upstream error: %s" % e.response.status_code),
            )
        except httpx.RequestError as e:
            return JSONResponse(
                status_code=502,
                content=error_envelope("UPSTREAM_ERROR", "Upstream request failed: %s" % str(e)),
            )

    pages_data, extract_err = _extract_pages_from_pdf(resp.content)
    if extract_err:
        return extract_err

    result = _build_preflight_result(pages_data, doc_id, ws_id, file_url)

    logger.info(
        "[PREFLIGHT] run complete: doc=%s ws=%s gate=%s mode=%s pages=%d",
        doc_id, ws_id, result["gate_color"], result["doc_mode"],
        result["metrics"]["total_pages"],
    )

    return JSONResponse(status_code=200, content=envelope(result))


@router.post("/upload")
async def preflight_upload(
    request: Request,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    """Run preflight on an uploaded PDF (base64-encoded). Internal/Test Lab use."""
    if isinstance(auth, JSONResponse):
        return auth

    flag_check = require_preflight()
    if flag_check:
        return flag_check

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid JSON body"),
        )

    ws_id, ws_err = _resolve_workspace(request, auth, body)
    if ws_err:
        return ws_err

    admin_err = _require_admin_sandbox(auth, ws_id)
    if admin_err:
        return admin_err

    pdf_base64 = body.get("pdf_base64", "").strip()
    filename = body.get("filename", "uploaded.pdf").strip()
    doc_id = body.get("doc_id", "").strip()

    if not pdf_base64:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "pdf_base64 is required"),
        )

    import base64
    try:
        pdf_bytes = base64.b64decode(pdf_base64)
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid base64 encoding"),
        )

    from server.pdf_proxy import MAX_SIZE_BYTES
    if len(pdf_bytes) > MAX_SIZE_BYTES:
        return JSONResponse(
            status_code=413,
            content=error_envelope("FILE_TOO_LARGE", "File exceeds size limit"),
        )

    if not doc_id:
        doc_id = derive_cache_identity(ws_id, "upload://%s" % filename)

    pages_data, extract_err = _extract_pages_from_pdf(pdf_bytes)
    if extract_err:
        return extract_err

    file_url = "upload://%s" % filename
    result = _build_preflight_result(pages_data, doc_id, ws_id, file_url)

    logger.info(
        "[PREFLIGHT] upload complete: doc=%s ws=%s gate=%s mode=%s pages=%d",
        doc_id, ws_id, result["gate_color"], result["doc_mode"],
        result["metrics"]["total_pages"],
    )

    return JSONResponse(status_code=200, content=envelope(result))


@router.get("/{doc_id}")
async def preflight_read(
    doc_id: str,
    request: Request,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    """Read cached preflight result."""
    if isinstance(auth, JSONResponse):
        return auth

    flag_check = require_preflight()
    if flag_check:
        return flag_check

    ws_id, ws_err = _resolve_workspace(request, auth)
    if ws_err:
        return ws_err

    admin_err = _require_admin_sandbox(auth, ws_id)
    if admin_err:
        return admin_err

    ck = _cache_key(ws_id, doc_id)
    cached = _preflight_cache.get(ck)

    if not cached:
        return JSONResponse(
            status_code=404,
            content=error_envelope("NOT_FOUND", "No preflight result cached for doc_id: %s" % doc_id),
        )

    return JSONResponse(status_code=200, content=envelope(cached))


@router.post("/action")
async def preflight_action(
    request: Request,
    auth=Depends(require_auth(AuthClass.EITHER)),
):
    """Handle Accept Risk or Escalate OCR actions."""
    if isinstance(auth, JSONResponse):
        return auth

    flag_check = require_preflight()
    if flag_check:
        return flag_check

    try:
        body = await request.json()
    except Exception:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "Invalid JSON body"),
        )

    ws_id, ws_err = _resolve_workspace(request, auth, body)
    if ws_err:
        return ws_err

    admin_err = _require_admin_sandbox(auth, ws_id)
    if admin_err:
        return admin_err

    doc_id = body.get("doc_id", "").strip()
    action = body.get("action", "").strip()
    patch_id = body.get("patch_id", "").strip()

    if not doc_id or not action:
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "doc_id and action are required"),
        )

    if action not in ("accept_risk", "escalate_ocr"):
        return JSONResponse(
            status_code=400,
            content=error_envelope("VALIDATION_ERROR", "action must be 'accept_risk' or 'escalate_ocr'"),
        )

    ck = _cache_key(ws_id, doc_id)
    cached = _preflight_cache.get(ck)
    if not cached:
        return JSONResponse(
            status_code=404,
            content=error_envelope("NOT_FOUND", "No preflight result for doc_id: %s" % doc_id),
        )

    gate = cached.get("gate_color", "RED")
    if action == "accept_risk" and gate == "RED":
        return JSONResponse(
            status_code=400,
            content=error_envelope("GATE_BLOCKED", "Cannot accept risk on RED gate. Must escalate to OCR."),
        )

    result = {
        "doc_id": doc_id,
        "action": action,
        "gate_color": gate,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "actor_id": auth.user_id,
    }

    cached["action_taken"] = action
    cached["action_timestamp"] = result["timestamp"]
    cached["action_actor"] = auth.user_id

    if patch_id:
        evidence_pack_id = generate_id("evp_")
        result["evidence_pack_id"] = evidence_pack_id
        result["patch_metadata"] = {
            "preflight_summary": {
                "doc_id": doc_id,
                "gate_color": gate,
                "doc_mode": cached.get("doc_mode"),
                "action": action,
                "metrics": cached.get("metrics"),
            },
            "system_evidence_pack_id": evidence_pack_id,
        }
        cached["materialized"] = True
        cached["evidence_pack_id"] = evidence_pack_id
        logger.info("[PREFLIGHT] action=%s doc=%s patch=%s evp=%s", action, doc_id, patch_id, evidence_pack_id)
    else:
        logger.info("[PREFLIGHT] action=%s doc=%s (no patch, cache-only)", action, doc_id)

    return JSONResponse(status_code=200, content=envelope(result))
