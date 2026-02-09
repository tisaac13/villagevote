"""
Redis caching layer for frequently accessed data.

Caches representatives, user profiles, and other hot-path data
to avoid redundant DB queries and external API calls.
"""
import json
import logging
from typing import Optional, Any

import redis.asyncio as aioredis

from app.core.config import settings

logger = logging.getLogger(__name__)

# Connection pool shared across the application
_pool: Optional[aioredis.Redis] = None


async def get_redis() -> Optional[aioredis.Redis]:
    """Get or create the global Redis connection pool."""
    global _pool
    if _pool is None:
        try:
            _pool = aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
            )
            await _pool.ping()
            logger.info("Redis cache connected")
        except Exception as e:
            logger.warning(f"Redis unavailable, caching disabled: {e}")
            _pool = None
    return _pool


async def close_redis():
    """Cleanly close Redis pool on shutdown."""
    global _pool
    if _pool:
        await _pool.close()
        _pool = None


# --------------- helpers ---------------

async def cache_get(key: str) -> Optional[Any]:
    """Retrieve a JSON-serialized value from cache."""
    r = await get_redis()
    if r is None:
        return None
    try:
        raw = await r.get(key)
        return json.loads(raw) if raw else None
    except Exception as e:
        logger.debug(f"Cache get failed for {key}: {e}")
        return None


async def cache_set(key: str, value: Any, ttl: int = 300):
    """Store a JSON-serializable value with a TTL (seconds, default 5 min)."""
    r = await get_redis()
    if r is None:
        return
    try:
        await r.set(key, json.dumps(value, default=str), ex=ttl)
    except Exception as e:
        logger.debug(f"Cache set failed for {key}: {e}")


async def cache_delete(key: str):
    """Delete a single cache key."""
    r = await get_redis()
    if r is None:
        return
    try:
        await r.delete(key)
    except Exception as e:
        logger.debug(f"Cache delete failed for {key}: {e}")


async def cache_delete_pattern(pattern: str):
    """Delete all keys matching a pattern (e.g. 'user:*:reps')."""
    r = await get_redis()
    if r is None:
        return
    try:
        cursor = "0"
        while cursor != 0:
            cursor, keys = await r.scan(cursor=cursor, match=pattern, count=100)
            if keys:
                await r.delete(*keys)
    except Exception as e:
        logger.debug(f"Cache pattern delete failed for {pattern}: {e}")


# --------------- key builders ---------------

def reps_key(user_id) -> str:
    return f"user:{user_id}:reps"


def dashboard_key(user_id) -> str:
    return f"user:{user_id}:dashboard"


def congress_members_key(state_code: str) -> str:
    return f"congress:members:{state_code.upper()}"
