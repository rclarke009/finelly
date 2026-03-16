"""
Remote log sender: fire-and-forget POST of sanitized log payloads to Supabase Edge Function (Option B).
No PII. Only used when REMOTE_LOG_URL is set.
"""

import asyncio
import logging
from datetime import datetime, timezone

import httpx

from app.config import REMOTE_LOG_INSTANCE_ID, REMOTE_LOG_SECRET, REMOTE_LOG_URL, SUPABASE_ANON_KEY
from app.models import RemoteLogEventPayload

logger = logging.getLogger(__name__)


def _utc_iso_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def send_remote_log(
    level: str,
    message: str,
    *,
    route: str | None = None,
    request_id: str | None = None,
    trace_id: str | None = None,
    duration_ms: int | None = None,
    error_type: str | None = None,
    stack_trace: str | None = None,
) -> None:
    """Fire-and-forget: if REMOTE_LOG_URL is set, POST payload to Edge Function. Does not block."""
    if not REMOTE_LOG_URL:
        return
    payload = RemoteLogEventPayload(
        timestamp=_utc_iso_now(),
        level=level,
        message=message[:2000],
        route=route,
        request_id=request_id,
        trace_id=trace_id,
        duration_ms=duration_ms,
        error_type=error_type,
        stack_trace=stack_trace[:5000] if stack_trace else None,
        instance_id=REMOTE_LOG_INSTANCE_ID or None,
    )
    asyncio.create_task(_post_remote_log(payload))


async def _post_remote_log(payload: RemoteLogEventPayload) -> None:
    try:
        headers = {"Content-Type": "application/json"}
        if REMOTE_LOG_SECRET:
            headers["X-Remote-Log-Secret"] = REMOTE_LOG_SECRET
        if SUPABASE_ANON_KEY:
            headers["Authorization"] = f"Bearer {SUPABASE_ANON_KEY}"
        async with httpx.AsyncClient(timeout=10.0) as client:
            r = await client.post(REMOTE_LOG_URL, json=payload.model_dump(mode="json"), headers=headers)
            if r.status_code >= 400:
                logger.debug("Remote log POST failed: %s %s", r.status_code, r.text)
    except Exception as e:
        logger.debug("Remote log send error: %s", e)
