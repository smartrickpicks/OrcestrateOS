"""
Salesforce Entity Resolver — Stub Interface (v0)

Contract:
    resolve_entity(workspace_id, name, address=None) ->
        {
            "classification": str,        # e.g. "Account", "Contact", "Lead", "Unknown"
            "score": float,               # 0.0–1.0 confidence in match
            "candidates": list[dict],     # ranked candidate matches from Salesforce
            "explanation": str,           # human-readable reasoning
            "provider": str,              # "salesforce_mock" | "salesforce_live"
            "resolved": bool,             # whether a confident match was found
        }

Integration point:
    This resolver is additive — its output feeds as a confidence signal
    into the existing suggestion engine scoring pipeline. It does NOT
    replace or override any existing matching logic.

Current status:
    STUB ONLY — no network calls, no Salesforce API usage.
    Gated behind SALESFORCE_RESOLVER_ENABLED feature flag (default: off).
"""

import logging

logger = logging.getLogger(__name__)

SALESFORCE_RESOLVER_ENABLED = False

_EMPTY_RESULT = {
    "classification": "Unknown",
    "score": 0.0,
    "candidates": [],
    "explanation": "Salesforce resolver is not enabled",
    "provider": "salesforce_mock",
    "resolved": False,
}


def is_resolver_enabled():
    return SALESFORCE_RESOLVER_ENABLED


def resolve_entity(workspace_id, name, address=None):
    if not SALESFORCE_RESOLVER_ENABLED:
        return dict(_EMPTY_RESULT)

    logger.info(
        "[SF_RESOLVER] stub resolve_entity: ws=%s name=%s address=%s",
        workspace_id, name, address,
    )

    return {
        "classification": "Unknown",
        "score": 0.0,
        "candidates": [],
        "explanation": "Mock resolver — no live Salesforce connection configured",
        "provider": "salesforce_mock",
        "resolved": False,
    }


def get_resolver_status():
    return {
        "enabled": SALESFORCE_RESOLVER_ENABLED,
        "provider": "salesforce_mock",
        "ready_for_integration": True,
        "live_api": False,
        "notes": "Stub interface only. Enable SALESFORCE_RESOLVER_ENABLED to activate mock responses.",
    }
