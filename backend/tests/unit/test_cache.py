"""Cache backends, generation-based invalidation and the Redis rate limiter."""

import fakeredis
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core import cache as cache_module
from app.core.cache import MemoryCache, RedisCache, get_or_compute
from app.core.rate_limit import RedisRateLimitStore


def test_memory_cache_ttl_and_incr(monkeypatch):
    c = MemoryCache()
    c.set("a", "1", ttl=60)
    assert c.get("a") == "1"
    assert c.incr("n") == 1 and c.incr("n") == 2
    clock = [1000.0]
    monkeypatch.setattr(cache_module.time, "monotonic", lambda: clock[0])
    c.set("short", "x", ttl=5)
    clock[0] += 6
    assert c.get("short") is None


def test_redis_cache_round_trip():
    c = RedisCache(fakeredis.FakeRedis(decode_responses=True))
    c.set("k", "v", ttl=60)
    assert c.get("k") == "v"
    assert c.incr("gen") == 1


def test_redis_errors_behave_like_a_miss():
    class Broken:
        def get(self, *a, **k): raise ConnectionError("down")
        def set(self, *a, **k): raise ConnectionError("down")
        def incr(self, *a, **k): raise ConnectionError("down")

    c = RedisCache(Broken())
    assert c.get("k") is None
    c.set("k", "v", ttl=1)  # no exception
    assert c.incr("g") == 0


async def test_get_or_compute_caches_until_the_generation_changes(monkeypatch):
    monkeypatch.setattr(cache_module, "cache", MemoryCache())
    calls = []

    async def compute():
        calls.append(1)
        return {"n": len(calls)}

    first = await get_or_compute("t", "org1", "org", {"days": 30}, compute)
    second = await get_or_compute("t", "org1", "org", {"days": 30}, compute)
    assert first == second == {"n": 1} and len(calls) == 1
    other_params = await get_or_compute("t", "org1", "org", {"days": 7}, compute)
    assert other_params == {"n": 2}

    cache_module.bump_generation("org1")
    assert await get_or_compute("t", "org1", "org", {"days": 30}, compute) == {"n": 3}


def test_commits_bump_the_generation_of_touched_organizations(monkeypatch):
    from app.db.models import AuditLog
    from app.db.session import Base

    monkeypatch.setattr(cache_module, "cache", MemoryCache())
    engine = create_engine("sqlite://")
    Base.metadata.create_all(engine, tables=[AuditLog.__table__])
    with Session(engine) as session:
        session.add(AuditLog(organization_id="org-a", action="test"))
        session.commit()
        session.add(AuditLog(organization_id="org-b", action="test"))
        session.rollback()  # rolled-back writes don't invalidate
    assert cache_module.cache.get("tw:gen:org-a") == "1"
    assert cache_module.cache.get("tw:gen:org-b") is None


def test_redis_rate_limit_window():
    store = RedisRateLimitStore(fakeredis.FakeRedis())
    assert [store.hit("ip", 2, 60) for _ in range(2)] == [None, None]
    assert store.hit("ip", 2, 60) > 0
    assert store.hit("other", 2, 60) is None
