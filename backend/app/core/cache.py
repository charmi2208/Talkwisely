"""
Caching (docs/SPEC.md §58): analytics, Copilot answers and job status.

Backends (``CACHE_BACKEND``):
- ``memory`` (default): per process. Fine for one API process with in-process jobs.
- ``redis``: shared by every API replica and Celery worker (``CACHE_URL``, defaults to
  ``REDIS_URL``). Use it whenever processing runs on Celery.
- ``none``: caching off.

Invalidation is by generation: every cached value for an organization is keyed with that
organization's current generation number, and any database commit that touched a row
belonging to the organization increments it (see ``install_invalidation``). Old entries
are never read again and simply expire. This keeps caching safe without listing every
write path by hand.

Redis errors never break a request: the cache behaves as a miss and the error is logged.
"""

import asyncio
import hashlib
import json
import threading
import time
from typing import Any, Awaitable, Callable, Protocol

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("core.cache")


class CacheBackend(Protocol):
    name: str

    def get(self, key: str) -> str | None: ...
    def set(self, key: str, value: str, ttl: int) -> None: ...
    def incr(self, key: str) -> int: ...


class MemoryCache:
    name = "memory"

    def __init__(self, max_entries: int = 5000) -> None:
        self._data: dict[str, tuple[float | None, str]] = {}
        self._lock = threading.Lock()
        self._max = max_entries

    def get(self, key: str) -> str | None:
        with self._lock:
            item = self._data.get(key)
            if not item:
                return None
            expires, value = item
            if expires is not None and expires < time.monotonic():
                del self._data[key]
                return None
            return value

    def set(self, key: str, value: str, ttl: int) -> None:
        with self._lock:
            if len(self._data) >= self._max:
                now = time.monotonic()
                for k in [k for k, (exp, _) in self._data.items() if exp is not None and exp < now]:
                    del self._data[k]
                if len(self._data) >= self._max:
                    self._data.pop(next(iter(self._data)))
            self._data[key] = (time.monotonic() + ttl if ttl else None, value)

    def incr(self, key: str) -> int:
        with self._lock:
            _, value = self._data.get(key, (None, "0"))
            new = int(value) + 1
            self._data[key] = (None, str(new))
            return new

    def clear(self) -> None:
        with self._lock:
            self._data.clear()


class RedisCache:
    name = "redis"

    def __init__(self, client) -> None:
        self._client = client
        self._warned = False

    @classmethod
    def from_url(cls, url: str) -> "RedisCache":
        import redis

        return cls(redis.Redis.from_url(url, decode_responses=True, socket_timeout=0.5, socket_connect_timeout=0.5))

    def _failed(self, op: str, error: Exception) -> None:
        if not self._warned:  # avoid a log line per request while Redis is down
            logger.warning("Redis cache unavailable; continuing without it", op=op, error=str(error))
            self._warned = True

    def get(self, key: str) -> str | None:
        try:
            value = self._client.get(key)
            self._warned = False
            return value
        except Exception as e:
            self._failed("get", e)
            return None

    def set(self, key: str, value: str, ttl: int) -> None:
        try:
            self._client.set(key, value, ex=ttl or None)
        except Exception as e:
            self._failed("set", e)

    def incr(self, key: str) -> int:
        try:
            return int(self._client.incr(key))
        except Exception as e:
            self._failed("incr", e)
            return 0


class NullCache:
    name = "none"

    def get(self, key: str) -> str | None:
        return None

    def set(self, key: str, value: str, ttl: int) -> None:
        pass

    def incr(self, key: str) -> int:
        return 0


def _build() -> CacheBackend:
    if settings.cache_backend == "redis":
        return RedisCache.from_url(settings.cache_url or settings.redis_url)
    if settings.cache_backend == "none":
        return NullCache()
    return MemoryCache()


cache: CacheBackend = _build()


async def _call(fn, *args):
    """Redis calls are blocking; keep them off the event loop."""
    if cache.name == "redis":
        return await asyncio.to_thread(fn, *args)
    return fn(*args)


# ---------------------------------------------------------------------------
# Generations (invalidation)
# ---------------------------------------------------------------------------

def _gen_key(organization_id: str) -> str:
    return f"tw:gen:{organization_id}"


def bump_generation(organization_id: str) -> None:
    cache.incr(_gen_key(organization_id))


async def generation(organization_id: str) -> str:
    return (await _call(cache.get, _gen_key(organization_id))) or "0"


def install_invalidation() -> None:
    """Bump an organization's generation after any commit that wrote one of its rows."""
    from sqlalchemy import event
    from sqlalchemy.orm import Session

    if getattr(install_invalidation, "_installed", False):
        return

    @event.listens_for(Session, "after_flush")
    def _collect(session, _context):
        orgs = session.info.setdefault("tw_cache_orgs", set())
        for obj in (*session.new, *session.dirty, *session.deleted):
            org = obj.__dict__.get("organization_id")  # never triggers a lazy load
            if org:
                orgs.add(org)

    @event.listens_for(Session, "after_commit")
    def _bump(session):
        for org in session.info.pop("tw_cache_orgs", set()):
            bump_generation(org)

    @event.listens_for(Session, "after_rollback")
    def _discard(session):
        session.info.pop("tw_cache_orgs", None)

    install_invalidation._installed = True


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _key(namespace: str, organization_id: str, gen: str, scope: str, params: dict[str, Any]) -> str:
    digest = hashlib.sha256(json.dumps(params, sort_keys=True, default=str).encode()).hexdigest()[:24]
    return f"tw:{namespace}:{organization_id}:{gen}:{scope}:{digest}"


async def get_or_compute(
    namespace: str,
    organization_id: str,
    scope: str,
    params: dict[str, Any],
    compute: Callable[[], Awaitable[Any]],
    ttl: int | None = None,
) -> Any:
    """Return the cached JSON value, or compute, store and return it.

    ``scope`` separates results that differ by viewer (e.g. an agent's own data vs the
    whole organization). Values must be JSON-serializable.
    """
    if cache.name == "none":
        return await compute()
    key = _key(namespace, organization_id, await generation(organization_id), scope, params)
    hit = await _call(cache.get, key)
    if hit is not None:
        return json.loads(hit)
    value = await compute()
    await _call(cache.set, key, json.dumps(value, default=str), ttl or settings.cache_ttl_seconds)
    return value


# Job status: written by the worker (sync), read by the processing-status endpoint
JOB_STATUS_TTL = 3600


def set_job_status(conversation_id: str, status: dict) -> None:
    cache.set(f"tw:job:{conversation_id}", json.dumps(status, default=str), JOB_STATUS_TTL)


async def get_job_status(conversation_id: str) -> dict | None:
    raw = await _call(cache.get, f"tw:job:{conversation_id}")
    return json.loads(raw) if raw else None
