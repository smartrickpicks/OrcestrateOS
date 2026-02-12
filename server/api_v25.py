import logging
import uuid
from datetime import datetime, timezone

from fastapi import APIRouter

from server.db import check_health

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v2.5")


def _meta(request_id=None):
    return {
        "request_id": request_id or ("req_" + uuid.uuid4().hex[:12]),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


def envelope(data, request_id=None):
    return {"data": data, "meta": _meta(request_id)}


def collection_envelope(data, cursor=None, has_more=False, limit=50, request_id=None):
    meta = _meta(request_id)
    meta["pagination"] = {
        "cursor": cursor,
        "has_more": has_more,
        "limit": limit,
    }
    return {"data": data, "meta": meta}


def error_envelope(code, message, details=None, request_id=None):
    err = {"code": code, "message": message}
    if details is not None:
        err["details"] = details
    return {"error": err, "meta": _meta(request_id)}


@router.get("/health")
def health_check():
    db_ok = check_health()
    if db_ok:
        return {"status": "ok", "db": "connected", "version": "2.5.0"}
    else:
        from fastapi.responses import JSONResponse
        return JSONResponse(
            status_code=503,
            content={"status": "degraded", "db": "disconnected", "version": "2.5.0"},
        )
