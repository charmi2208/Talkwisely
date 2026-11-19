"""
Request rate limiting.

A sliding-window limiter keyed by client IP. Authentication endpoints get a much lower
limit than the rest of the API to slow down password guessing.

The in-memory store works for a single API process. ``RateLimitStore`` is the seam for a
shared store (e.g. Redis) when the API runs as several replicas.
"""

import time
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


store: RateLimitStore = MemoryRateLimitStore()


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

    retry_after = store.hit(key, limit, window)
    if retry_after is not None:
        return JSONResponse(
            status_code=429,
            content={"detail": "Too many requests. Please wait a moment and try again."},
            headers={"Retry-After": str(max(1, round(retry_after)))},
        )
    return await call_next(request)
