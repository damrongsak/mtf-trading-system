"""
H1: Per-Command Rate Limiter (Tiered).
Pattern: Interactive Brokers category-based order limits.

Categories:
    TRADE  → execute, amend, close  → 5 rps   (prevents order flood)
    MANAGE → cancel                 → 20 rps  (cancel must always be fast)
    READ   → get_account, get_orders, get_trades → 50 rps (safe for UI polling)

Mechanism: Redis Sliding Window Counter (INCR + EXPIRE per 1-second bucket).
    Key format: rate:{api_key}:{category}
    TTL: 1 second (auto-expires on second boundary)

Fail-open: If Redis is unavailable, the limiter allows the request and logs
a warning. Trading must not be blocked by infrastructure issues.

Usage:
    from app.utils.rate_limiter import command_rate_limiter

    result = await command_rate_limiter.check(api_key, cmd)
    if result.is_limited:
        return {"status": "rate_limited", "retry_after": 1, "category": result.category}
"""
import logging
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)

# ── Category definitions ───────────────────────────────────────────────────────

# Maps command → (category_name, limit_per_second)
_CMD_LIMITS: dict[str, tuple[str, int]] = {
    # TRADE: low limit — accidental flood prevention
    "execute": ("TRADE", 5),
    "amend":   ("TRADE", 5),
    "close":   ("TRADE", 5),
    # MANAGE: cancel must be fast and reliable
    "cancel":  ("MANAGE", 20),
    # READ: safe for aggressive UI polling
    "get_account": ("READ", 50),
    "get_orders":  ("READ", 50),
    "get_trades":  ("READ", 50),
}


@dataclass
class RateLimitResult:
    is_limited: bool
    category: str
    limit: int
    current_count: int

    def to_response(self) -> dict:
        """Standard rate-limited WS response."""
        return {
            "status": "rate_limited",
            "error": (
                f"Rate limit exceeded for {self.category} commands. "
                f"Limit: {self.limit} rps. "
                f"Current: {self.current_count}. "
                f"Retry in 1 second."
            ),
            "retry_after": 1,
            "category": self.category,
            "limit": self.limit,
        }


class CommandRateLimiter:
    """
    Redis-backed per-command-category rate limiter.
    
    Uses atomic INCR + EXPIRE to implement a sliding 1-second window.
    Singleton instance `command_rate_limiter` is shared across all WS connections.
    """

    async def check(self, api_key: str, cmd: str) -> RateLimitResult:
        """
        Check if the command is within rate limits.
        
        Args:
            api_key: The client's API key (used as rate limit partition key)
            cmd:     The command name (e.g., 'execute', 'get_account')

        Returns:
            RateLimitResult with is_limited=True if limit exceeded.
            If command is unknown or Redis fails, returns is_limited=False (fail-open).
        """
        if cmd not in _CMD_LIMITS:
            # Unknown/read-only system commands — allow through
            return RateLimitResult(is_limited=False, category="UNKNOWN", limit=999, current_count=0)

        category, limit = _CMD_LIMITS[cmd]
        redis_key = f"rate:{api_key[:16]}:{category}"  # Truncate key for safety

        try:
            from app.utils.redis_client import redis_client
            rc = await redis_client.get_client()

            # Atomic: increment counter and set TTL (pipeline for atomicity)
            pipe = rc.pipeline()
            pipe.incr(redis_key)
            pipe.expire(redis_key, 1)  # 1-second TTL sliding window
            results = await pipe.execute()

            current_count = results[0]  # Value after INCR

            if current_count > limit:
                logger.warning(
                    f"[H1] Rate limit exceeded: api_key={api_key[:8]}... "
                    f"cmd={cmd} category={category} "
                    f"count={current_count}/{limit}"
                )
                return RateLimitResult(
                    is_limited=True,
                    category=category,
                    limit=limit,
                    current_count=current_count,
                )

            return RateLimitResult(
                is_limited=False,
                category=category,
                limit=limit,
                current_count=current_count,
            )

        except Exception as e:
            # Fail-open: Redis unavailable → allow request, log warning
            logger.warning(
                f"[H1] Rate limiter Redis error (fail-open): {e}. "
                f"cmd={cmd} api_key={api_key[:8]}..."
            )
            return RateLimitResult(is_limited=False, category=category, limit=limit, current_count=0)


# Singleton — shared across all WebSocket connections and HTTP requests
command_rate_limiter = CommandRateLimiter()
