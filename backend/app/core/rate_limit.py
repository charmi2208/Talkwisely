"""
Request rate limiting.

A sliding-window limiter keyed by client IP. Authentication endpoints get a much lower
limit than the rest of the API to slow down password guessing.

The in-memory store works for a single API process. With ``CACHE_BACKEND=redis`` the
limiter uses Redis instead, so every API replica shares the same counts.
"""

import asyncio
import time
import uuid
from collections import defaultdict, deque
from typing import Protocol

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.config import settings

AUTH_PATHS = ("/api/v1/auth/login", "/api/v1/auth/register", "/api/v1/auth/forgot-password", "/api/v1/auth/reset-password")
AUTH_LIMIT = 10  # requests per window, per IP, across the auth endpoints


class RateLimitStore(Protocol):
    def hit(self, key: str, limit: int, window_seconds: int) -> float | None:
        """Record a request; return seconds to wait if over the limit, else None."""


class MemoryRateLimitStore:
    def __init__(self) -> None:
        self._hits: dict[str, deque[float]] = defaultdict(deque)

    def hit(self, key: str, limit: int, window_seconds: int) -> float | None:
        now = time.monotonic()
        hits = self._hits[key]
        while hits and hits[0] <= now - window_seconds:
            hits.popleft()
        if len(hits) >= limit:
            return max(0.0, hits[0] + window_seconds - now)
        hits.append(now)
        return None

    def reset(self) -> None:
        self._hits.clear()


class RedisRateLimitStore:
    """Sliding window in a Redis sorted set per key (shared across processes)."""

    def __init__(self, client) -> None:
        self._client = client

    def hit(self, key: str, limit: int, window_seconds: int) -> float | None:
        now = time.time()
        redis_key = f"tw:ratelimit:{key}"
        try:
            pipe = self._client.pipeline()
            pipe.zremrangebyscore(redis_key, 0, now - window_seconds)
            pipe.zcard(redis_key)
            pipe.zrange(redis_key, 0, 0, withscores=True)
            _, count, oldest = pipe.execute()
            if count >= limit:
                return max(0.0, oldest[0][1] + window_seconds - now) if oldest else float(window_seconds)
            pipe = self._client.pipeline()
            pipe.zadd(redis_key, {f"{now}:{uuid.uuid4().hex[:8]}": now})
            pipe.expire(redis_key, window_seconds)
            pipe.execute()
        except Exception:
            return None  # fail open: Redis trouble shouldn't take the API down
        return None


def _build_store() -> RateLimitStore:
    if settings.cache_backend == "redis":
        import redis

        client = redis.Redis.from_url(
            settings.cache_url or settings.redis_url, socket_timeout=0.5, socket_connect_timeout=0.5
        )
        return RedisRateLimitStore(client)
    return MemoryRateLimitStore()


store: RateLimitStore = _build_store()


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


async def rate_limit_middleware(request: Request, call_next):
    # CORS preflights are answered by the CORS middleware and don't count
    if not settings.rate_limit_enabled or request.method == "OPTIONS" or not request.url.path.startswith("/api/"):
        return await call_next(request)

    window = settings.rate_limit_period_seconds
    ip = _client_ip(request)
    if request.method == "POST" and request.url.path in AUTH_PATHS:
        key, limit = f"auth:{ip}", AUTH_LIMIT
    else:
        key, limit = f"api:{ip}", settings.rate_limit_requests

    if isinstance(store, MemoryRateLimitStore):
        retry_after = store.hit(key, limit, window)
    else:
        retry_after = await asyncio.to_thread(store.hit, key, limit, window)
    if retry_after is not None:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please wait a moment and try again."},
            headers={"Retry-After": str(max(1, round(retry_after)))},
        )
    return await call_next(request)
