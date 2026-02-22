import logging

logger = logging.getLogger(__name__)


def trigger_session_handoff(
    workspace_id: str,
    actor_id: str,
    trigger: str,
    source_type: str,
    source_ref: str,
    environment=None,
    metadata: dict | None = None,
):
    logger.info(
        "custody_canary handoff: ws=%s actor=%s trigger=%s src=%s ref=%s",
        workspace_id,
        actor_id,
        trigger,
        source_type,
        source_ref,
    )
