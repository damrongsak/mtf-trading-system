"""
H2: Fill Event Publisher — Execution Service side.

After a broker confirms an order fill (FILLED/REJECTED/PARTIALLY_FILLED),
this module publishes a structured event to:
  1. Redis List  `execution:fills:{account_id}` — WS push delivery to API Gateway
  2. Redis Stream `execution.filled.stream`   — FillTradeConsumer → DB persistence (HFT-Lite compliant)

Event schema:
{
    "trace_id":    str,    # Matches the original WS command `id`
    "order_id":    str,    # Broker order ID
    "account_id":  str,    # Broker account ID (numeric cTrader ID)
    "status":      str,    # "FILLED" | "REJECTED" | "PARTIALLY_FILLED"
    "fill_price":  float,  # Actual execution price (0 if not filled)
    "fill_volume": float,  # Filled volume in universal units
    "instrument":  str,    # Symbol (e.g., "XAU_USD")
    "fill_time":   float,  # Unix timestamp of fill
    "reason":      str,    # Optional rejection reason
    "sl_price":    float,  # Stop-loss at time of fill (0 if none)
    "tp_price":    float,  # Take-profit at time of fill (0 if none)
    "direction":   str,    # "LONG" | "SHORT"
    "comment":     str,    # Order comment / strategy name
}
"""
import json
import logging
import time
from typing import Optional
from tenacity import retry, wait_exponential, stop_after_attempt, retry_if_exception_type

logger = logging.getLogger(__name__)

FILL_KEY_PREFIX = "execution:fills"
FILL_STREAM_KEY = "execution.filled.stream"
FILL_TTL = 300  # 5 minutes — fills are important, must not expire too fast
STREAM_MAXLEN = 10000  # Cap stream length to prevent unbounded growth

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    retry=retry_if_exception_type(Exception),
    reraise=False
)
async def publish_fill(
    account_id: str,
    trace_id: str,
    order_id: str,
    status: str,
    instrument: str,
    fill_price: float = 0.0,

    fill_volume: float = 0.0,
    reason: Optional[str] = None,
    sl_price: float = 0.0,
    tp_price: float = 0.0,
    direction: str = "LONG",
    comment: str = "",
) -> bool:
    """
    [H2] Publish a broker fill event to:
      - Redis List (WS push delivery to API Gateway)
      - Redis Stream (FillTradeConsumer → DB, HFT-Lite compliant)

    Returns True on success, False if Redis is unavailable (non-fatal).
    """
    import redis.asyncio as aioredis
    import os

    redis_key = f"{FILL_KEY_PREFIX}:{account_id}"

    payload = {
        "trace_id":    trace_id,
        "order_id":    str(order_id),
        "account_id":  str(account_id),
        "status":      status,
        "fill_price":  fill_price,
        "fill_volume": fill_volume,
        "instrument":  instrument,
        "fill_time":   time.time(),
        "reason":      reason or "",
        "sl_price":    sl_price,
        "tp_price":    tp_price,
        "direction":   direction,
        "comment":     comment,
    }
    payload_json = json.dumps(payload)

    try:
        rc = aioredis.from_url(os.environ.get("REDIS_URL", "redis://redis:6379/0"))
        async with rc:
            # 1. WS Push to API Gateway (List)
            await rc.lpush(redis_key, payload_json)
            await rc.expire(redis_key, FILL_TTL)

            # 2. Stream for FillTradeConsumer → DB persistence (HFT-Lite)
            # Redis Streams require field-value pairs — store as a single "data" field
            if status == "FILLED":
                await rc.xadd(
                    FILL_STREAM_KEY,
                    {"data": payload_json},
                    maxlen=STREAM_MAXLEN,
                    approximate=True,
                )

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
