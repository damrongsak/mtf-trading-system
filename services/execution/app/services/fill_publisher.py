"""
H2: Fill Event Publisher — Execution Service side.

After a broker confirms an order fill (FILLED/REJECTED/PARTIALLY_FILLED),
this module publishes a structured event to Redis so the API Gateway can
push a real-time callback to the originating WebSocket client.

Redis Key:  execution:fills:{account_id}
Type:       Redis List (LPUSH) — TTL 300s
Consumer:   API Gateway `_fill_subscriber_loop()` via BRPOP

Event schema:
{
    "trace_id":    str,    # Matches the original WS command `id`
    "order_id":    str,    # Broker order ID
    "account_id":  str,    # Broker account ID
    "status":      str,    # "FILLED" | "REJECTED" | "PARTIALLY_FILLED"
    "fill_price":  float,  # Actual execution price (0 if not filled)
    "fill_volume": float,  # Filled volume in lots
    "instrument":  str,    # Symbol (e.g., "XAU_USD")
    "fill_time":   float,  # Unix timestamp of fill
    "reason":      str,    # Optional rejection reason
}

Usage:
    from app.services.fill_publisher import publish_fill

    await publish_fill(
        account_id="67890",
        trace_id="client-cmd-uuid",
        order_id="broker-order-123",
        status="FILLED",
        fill_price=2055.50,
        fill_volume=0.01,
        instrument="XAU_USD",
    )
"""
import json
import logging
import time
from typing import Optional

logger = logging.getLogger(__name__)

FILL_KEY_PREFIX = "execution:fills"
FILL_TTL = 300  # 5 minutes — fills are important, must not expire too fast


async def publish_fill(
    account_id: str,
    trace_id: str,
    order_id: str,
    status: str,
    instrument: str,
    fill_price: float = 0.0,
    fill_volume: float = 0.0,
    reason: Optional[str] = None,
) -> bool:
    """
    [H2] Publish a broker fill event to Redis for WS push delivery.

    Returns True on success, False if Redis is unavailable (non-fatal).
    """
    redis_key = f"{FILL_KEY_PREFIX}:{account_id}"
    payload = json.dumps({
        "trace_id":    trace_id,
        "order_id":    str(order_id),
        "account_id":  str(account_id),
        "status":      status,
        "fill_price":  fill_price,
        "fill_volume": fill_volume,
        "instrument":  instrument,
        "fill_time":   time.time(),
        "reason":      reason or "",
    })

    try:
        # Import here to avoid circular imports at module load
        import redis.asyncio as aioredis
        import os
        rc = aioredis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
        async with rc:
            await rc.lpush(redis_key, payload)
            await rc.expire(redis_key, FILL_TTL)

        logger.info(
            f"[H2] Fill published: account={account_id} trace_id={trace_id} "
            f"status={status} price={fill_price} instrument={instrument}"
        )
        return True

    except Exception as e:
        # Non-fatal — the order was still placed; just the callback won't arrive
        logger.error(
            f"[H2] Failed to publish fill event: trace_id={trace_id} error={e}. "
            f"Order still executed — client will not receive fill callback."
        )
        return False
