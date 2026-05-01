"""
Redis Integration
==================
Singleton async Redis client with domain-specific helpers:
  • Rate limiting  (sliding window)
  • OTP storage    (auto-expiring keys)
  • Session cache  (JSON-serialised user sessions)
  • General cache  (get/set with TTL)
"""

import json
import time
from typing import Any, Optional

import redis.asyncio as aioredis

from app.config import get_settings

_redis_client: Optional[aioredis.Redis] = None


async def get_redis() -> aioredis.Redis:
    """Return (and lazily create) the async Redis connection pool."""
    global _redis_client
    if _redis_client is None:
        settings = get_settings()
        _redis_client = aioredis.from_url(
            settings.redis_url,
            decode_responses=True,
            max_connections=20,
        )
    return _redis_client


async def close_redis() -> None:
    """Gracefully close the pool on shutdown."""
    global _redis_client
    if _redis_client:
        await _redis_client.aclose()
        _redis_client = None


# ── Rate Limiting (sliding window) ────────────────────────

async def check_rate_limit(
    key: str,
    max_requests: int,
    window_seconds: int,
) -> tuple[bool, int]:
    """
    Sliding-window rate limiter.

    Returns (allowed: bool, remaining: int).
    """
    r = await get_redis()
    now = time.time()
    window_start = now - window_seconds
    pipe = r.pipeline()

    # Remove expired entries
    pipe.zremrangebyscore(key, 0, window_start)
    # Add current request
    pipe.zadd(key, {str(now): now})
    # Count requests in window
    pipe.zcard(key)
    # Set expiry on the key itself
    pipe.expire(key, window_seconds)

    results = await pipe.execute()
    current_count = results[2]
    allowed = current_count <= max_requests
    remaining = max(0, max_requests - current_count)
    return allowed, remaining


# ── OTP Storage ───────────────────────────────────────────

async def store_otp(email: str, otp_code: str, ttl_seconds: int = 300) -> None:
    """Store an OTP with automatic expiry."""
    r = await get_redis()
    key = f"otp:{email}"
    await r.setex(key, ttl_seconds, otp_code)


async def verify_otp(email: str, otp_code: str) -> bool:
    """Verify and consume an OTP (one-time use)."""
    r = await get_redis()
    key = f"otp:{email}"
    stored = await r.get(key)
    if stored and stored == otp_code:
        await r.delete(key)  # consume — single use
        return True
    return False


async def get_otp_attempts(email: str) -> int:
    """Track failed OTP attempts for brute-force protection."""
    r = await get_redis()
    key = f"otp_attempts:{email}"
    val = await r.get(key)
    return int(val) if val else 0


async def increment_otp_attempts(email: str, lockout_seconds: int = 900) -> int:
    """Increment failed attempts; auto-expire after lockout window."""
    r = await get_redis()
    key = f"otp_attempts:{email}"
    pipe = r.pipeline()
    pipe.incr(key)
    pipe.expire(key, lockout_seconds)
    results = await pipe.execute()
    return results[0]


async def clear_otp_attempts(email: str) -> None:
    r = await get_redis()
    await r.delete(f"otp_attempts:{email}")


# ── Session Cache ─────────────────────────────────────────

async def cache_session(session_id: str, data: dict, ttl_seconds: int = 1800) -> None:
    """Cache a user session as JSON."""
    r = await get_redis()
    await r.setex(f"session:{session_id}", ttl_seconds, json.dumps(data))


async def get_cached_session(session_id: str) -> Optional[dict]:
    """Retrieve a cached session."""
    r = await get_redis()
    raw = await r.get(f"session:{session_id}")
    return json.loads(raw) if raw else None


async def invalidate_session(session_id: str) -> None:
    r = await get_redis()
    await r.delete(f"session:{session_id}")


async def invalidate_all_user_sessions(user_id: str) -> int:
    """Invalidate every session for a user (logout-everywhere)."""
    r = await get_redis()
    pattern = f"session:*"
    deleted = 0
    async for key in r.scan_iter(match=pattern, count=100):
        raw = await r.get(key)
        if raw:
            data = json.loads(raw)
            if data.get("user_id") == user_id:
                await r.delete(key)
                deleted += 1
    return deleted


# ── General Cache ─────────────────────────────────────────

async def cache_set(key: str, value: Any, ttl_seconds: int = 300) -> None:
    r = await get_redis()
    await r.setex(f"cache:{key}", ttl_seconds, json.dumps(value))


async def cache_get(key: str) -> Optional[Any]:
    r = await get_redis()
    raw = await r.get(f"cache:{key}")
    return json.loads(raw) if raw else None


async def cache_delete(key: str) -> None:
    r = await get_redis()
    await r.delete(f"cache:{key}")
