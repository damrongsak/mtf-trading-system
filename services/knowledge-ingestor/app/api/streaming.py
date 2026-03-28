"""
SSE Streaming Endpoints — Knowledge Ingestor
============================================
GET  /stream/status/{task_id}  — Real-time pipeline progress via Redis Pub/Sub
POST /stream/llm               — Direct LLM streaming (token-by-token SSE)

Connection Management:
- Client disconnect detection on every poll cycle
- Redis Pub/Sub cleanup guaranteed in finally block
- Heartbeat comment every 15s keeps alive through nginx/proxies
- Configurable timeout (default 300s) auto-closes dead streams
"""

import json
import asyncio
import logging
from datetime import datetime
from typing import AsyncGenerator

import redis.asyncio as aioredis
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from app.core.app_config import config
from app.core.llm_utils import LLMUtils
from app.core.logger import get_logger

router = APIRouter()
logger = get_logger("OlympusStreaming")

_HEARTBEAT_INTERVAL = 15.0  # seconds between SSE keepalive comments
_POLL_INTERVAL = 0.1        # seconds between Redis message polls
_TERMINAL_STAGES = {"pipeline_done", "pipeline_failed", "skipped"}


def _make_async_redis() -> aioredis.Redis:
    """Create a short-lived async Redis client for pub/sub use."""
    return aioredis.Redis(
        host=config.falkor_host,
        port=config.falkor_port,
        decode_responses=True,
        socket_timeout=5,
        socket_connect_timeout=3,
    )


# ─────────────────────────── Task Progress Stream ────────────────────────────

@router.get(
    "/status/{task_id}",
    summary="Real-time task progress (SSE)",
    description=(
        "Subscribe to SSE events for an ingestion task. "
        "Events are pushed via Redis Pub/Sub channel `progress:{task_id}`. "
        "Stream closes when task reaches a terminal stage or timeout is reached."
    ),
)
async def stream_task_status(
    task_id: str,
    request: Request,
    timeout: int = 300,
):
    """
    SSE endpoint for pipeline progress monitoring.

    Event types emitted by the ingestion pipeline:
    - queued, doc_analysis_done
    - summary_start, summary_done
    - detail_start, detail_chunk_done, detail_done
    - committer_start, committer_done
    - enrichment_done
    - pipeline_done | pipeline_failed | skipped  (terminal — stream closes)
    - heartbeat (every 15s, keeps connection alive)
    """
    async def event_generator() -> AsyncGenerator[dict, None]:
        r = _make_async_redis()
        pubsub = r.pubsub()
        channel = f"progress:{task_id}"
        await pubsub.subscribe(channel)
        logger.info(f"📡 SSE subscribed → {channel}")

        elapsed = 0.0
        heartbeat_elapsed = 0.0

        try:
            while elapsed < timeout:
                # ── Client disconnect check ──────────────────────────────────
                if await request.is_disconnected():
                    logger.info(f"🔌 Client disconnected from {channel}")
                    break

                # ── Non-blocking Redis poll ──────────────────────────────────
                msg = await pubsub.get_message(
                    ignore_subscribe_messages=True,
                    timeout=_POLL_INTERVAL,
                )
                if msg and msg.get("type") == "message":
                    try:
                        payload = json.loads(msg["data"])
                        stage = payload.get("stage", "update")
                        logger.debug(f"📤 SSE→client: stage={stage} task={task_id}")
                        yield {"event": stage, "data": json.dumps(payload)}
                        if stage in _TERMINAL_STAGES:
                            logger.info(f"✅ Stream terminal: {stage} ({task_id})")
                            break
                    except json.JSONDecodeError:
                        logger.warning(f"Malformed pub/sub payload for {task_id}")

                # ── Heartbeat (prevents proxy timeout) ──────────────────────
                heartbeat_elapsed += _POLL_INTERVAL
                if heartbeat_elapsed >= _HEARTBEAT_INTERVAL:
                    yield {
                        "event": "heartbeat",
                        "data": json.dumps({"ts": datetime.now().isoformat(), "task_id": task_id}),
                    }
                    heartbeat_elapsed = 0.0

                elapsed += _POLL_INTERVAL
                await asyncio.sleep(0)  # yield to event loop

        except Exception as e:
            logger.error(f"SSE stream error ({task_id}): {e}")
            yield {"event": "error", "data": json.dumps({"message": str(e)})}
        finally:
            # Guaranteed cleanup — runs even on client disconnect
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
                await r.aclose()
                logger.info(f"🧹 SSE cleanup done for {task_id}")
            except Exception as cleanup_err:
                logger.warning(f"SSE cleanup error ({task_id}): {cleanup_err}")

    return EventSourceResponse(event_generator())


# ─────────────────────────── Direct LLM Stream ───────────────────────────────

class LLMStreamRequest(BaseModel):
    system_prompt: str
    user_prompt: str
    tier: str = "direct"
    max_tokens: int = 4000


@router.post(
    "/llm",
    summary="Direct LLM streaming (SSE)",
    description=(
        "Stream an ad-hoc LLM query with token-by-token SSE output. "
        "Uses the 3-tier cascading fallback. "
        "Emits: tier_start → delta × N → tier_done → done | fallback | error"
    ),
)
async def stream_llm(body: LLMStreamRequest, request: Request):
    """
    Direct LLM SSE streaming endpoint.

    Event types:
    - tier_start  {"tier_label": "direct-T1", "model": "stepfun/..."}
    - delta       {"text": "token..."}
    - tier_done   {"tokens": 342, "full_text": "..."}
    - fallback    {"from_tier": 1, "reason": "402 Insufficient credits"}
    - done        {"full_text": "...", "tier_used": 1}
    - error       {"message": "All 3 LLM tiers exhausted"}
    """
    async def event_generator() -> AsyncGenerator[dict, None]:
        try:
            async for event in LLMUtils.call_llm_streaming(
                system_prompt=body.system_prompt,
                user_prompt=body.user_prompt,
                tier=body.tier,
                max_tokens=body.max_tokens,
            ):
                if await request.is_disconnected():
                    logger.info("🔌 Client disconnected from /stream/llm")
                    break
                yield {"event": event["event"], "data": json.dumps(event["data"])}
        except Exception as e:
            logger.error(f"LLM stream error: {e}")
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())
