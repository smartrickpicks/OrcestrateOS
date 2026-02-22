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

PREFLIGHT_GATE_SYNC = "PREFLIGHT_GATE_SYNC"
PREFLIGHT_GATE_SYNC_ALIAS = "PREFLIGHT_GATE_SYNC_V251"

def is_preflight_enabled():
    """Check canonical flag or alias."""
    return is_enabled(PREFLIGHT_GATE_SYNC) or is_enabled(PREFLIGHT_GATE_SYNC_ALIAS)

def require_preflight():
    """Gate check returning 404 JSONResponse if preflight disabled."""
    if not is_preflight_enabled():
        return JSONResponse(
            status_code=404,
            content=error_envelope(
                "FEATURE_DISABLED",
                "Preflight Gate Sync is not enabled. Set PREFLIGHT_GATE_SYNC=true to activate.",
            ),
        )
    return None


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


PREFLIGHT_LAB = "PREFLIGHT_LAB"

def is_preflight_lab_enabled():
    return is_enabled(PREFLIGHT_LAB)


OPS_VIEW_DB_READ = "OPS_VIEW_DB_READ"
OPS_VIEW_DB_WRITE = "OPS_VIEW_DB_WRITE"

def is_ops_view_db_read():
    return is_enabled(OPS_VIEW_DB_READ)

def is_ops_view_db_write():
    return is_enabled(OPS_VIEW_DB_WRITE)


RECORD_INSPECTOR_V2 = "RECORD_INSPECTOR_V2"
RECORD_INSPECTOR_V2_DEFAULT = "RECORD_INSPECTOR_V2_DEFAULT"
RECORD_INSPECTOR_V2_LEGACY_HIDDEN = "RECORD_INSPECTOR_V2_LEGACY_HIDDEN"

def is_workspace_v2_enabled():
    """Check if Record Inspector V2 (Beta) workspace is enabled."""
    return is_enabled(RECORD_INSPECTOR_V2)

def is_workspace_v2_default():
    """Check if V2 workspace is the default PTL edit target."""
    return is_workspace_v2_enabled() and is_enabled(RECORD_INSPECTOR_V2_DEFAULT)

def require_workspace_v2():
    """Gate check returning 404 JSONResponse if workspace V2 disabled."""
    if not is_workspace_v2_enabled():
        return JSONResponse(
            status_code=404,
            content=error_envelope(
                "FEATURE_DISABLED",
                "Record Inspector V2 is not enabled. Set RECORD_INSPECTOR_V2=true to activate.",
            ),
        )
    return None
