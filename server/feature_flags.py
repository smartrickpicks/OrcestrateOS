import os
import logging
from fastapi.responses import JSONResponse
from server.api_v25 import error_envelope

logger = logging.getLogger(__name__)

_FLAG_CACHE = {}


def is_enabled(flag_name):
    if flag_name in _FLAG_CACHE:
        return _FLAG_CACHE[flag_name]
    val = os.environ.get(flag_name, "").strip().lower()
    enabled = val in ("true", "1", "yes", "on")
    _FLAG_CACHE[flag_name] = enabled
    return enabled


def clear_cache():
    _FLAG_CACHE.clear()


EVIDENCE_INSPECTOR = "EVIDENCE_INSPECTOR_V251"


def require_evidence_inspector():
    if not is_enabled(EVIDENCE_INSPECTOR):
        return JSONResponse(
            status_code=404,
            content=error_envelope(
                "FEATURE_DISABLED",
                "Evidence Inspector v2.51 is not enabled. Set EVIDENCE_INSPECTOR_V251=true to activate.",
            ),
        )
    return None
