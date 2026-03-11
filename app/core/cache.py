"""
SentinelFraud Cache Layer
Stage 7: Redis caching, session storage, cache invalidation
"""

import json
import logging
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import settings

logger = logging.getLogger(__name__)

redis_client: aioredis.Redis = None  # type: ignore


async def init_redis() -> None:
    global redis_client
    redis_client = aioredis.from_url(
        settings.REDIS_URL,
        max_connections=settings.REDIS_MAX_CONNECTIONS,
        encoding="utf-8",
        decode_responses=True,
    )
    await redis_client.ping()
    logger.info("Redis connected: %s", settings.REDIS_URL)


async def close_redis() -> None:
    if redis_client:
        await redis_client.close()


# ---------------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------------
async def cache_get(key: str) -> Optional[Any]:
    try:
        raw = await redis_client.get(key)
        return json.loads(raw) if raw else None
    except Exception as exc:
        logger.warning("Cache GET failed for '%s': %s", key, exc)
        return None


async def cache_set(key: str, value: Any, ttl: int = settings.CACHE_TTL_SECONDS) -> bool:
    try:
        await redis_client.setex(key, ttl, json.dumps(value, default=str))
        return True
    except Exception as exc:
        logger.warning("Cache SET failed for '%s': %s", key, exc)
        return False


async def cache_delete(key: str) -> bool:
    try:
        await redis_client.delete(key)
        return True
    except Exception as exc:
        logger.warning("Cache DELETE failed for '%s': %s", key, exc)
        return False


async def cache_delete_pattern(pattern: str) -> int:
    try:
        keys = await redis_client.keys(pattern)
        if keys:
            return await redis_client.delete(*keys)
        return 0
    except Exception as exc:
        logger.warning("Cache DELETE pattern '%s' failed: %s", pattern, exc)
        return 0


# ---------------------------------------------------------------------------
# Velocity counter helpers  (sliding-window, 1h TTL)
# ---------------------------------------------------------------------------
async def increment_velocity_counter(key: str, ttl: int = 3600) -> int:
    """Atomically increment a velocity counter, setting TTL on first write."""
    try:
        pipe = redis_client.pipeline()
        await pipe.incr(key)
        await pipe.expire(key, ttl)
        results = await pipe.execute()
        return int(results[0])
    except Exception as exc:
        logger.error("Velocity counter error for '%s': %s", key, exc)
        return 0


async def get_velocity_counter(key: str) -> int:
    try:
        val = await redis_client.get(key)
        return int(val) if val else 0
    except Exception:
        return 0


# ---------------------------------------------------------------------------
# Rate limiting  (Stage 5)
# ---------------------------------------------------------------------------
async def check_rate_limit(identifier: str, limit: int, window: int) -> tuple[bool, int]:
    """
    Returns (is_allowed, current_count).
    Uses fixed-window counter.
    """
    key = f"ratelimit:{identifier}"
    try:
        current = await redis_client.incr(key)
        if current == 1:
            await redis_client.expire(key, window)
        return current <= limit, current
    except Exception as exc:
        logger.error("Rate limit check failed: %s", exc)
        return True, 0  # fail open


# ---------------------------------------------------------------------------
# Risk score cache
# ---------------------------------------------------------------------------
async def cache_risk_score(transaction_id: str, result: dict) -> None:
    key = f"risk_score:{transaction_id}"
    await cache_set(key, result, ttl=settings.RISK_SCORE_TTL)


async def get_cached_risk_score(transaction_id: str) -> Optional[dict]:
    key = f"risk_score:{transaction_id}"
    return await cache_get(key)
