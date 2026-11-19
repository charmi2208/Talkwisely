"""Authentication, password reset, rate limiting and team management."""

import uuid

from app.core.security import create_password_reset_token
from tests.conftest import login


def _email() -> str:
    return f"user-{uuid.uuid4().hex[:8]}@example.com"


async def test_register_login_and_profile(client):
    email = _email()
    registered = await client.post("/api/v1/auth/register", json={
        "email": email, "password": "Password123", "full_name": "New Person", "organization_name": "Test Co",
    })
    assert registered.status_code == 201, registered.text

    headers = await login(client, email.upper(), "Password123")  # email match is case-insensitive
    me = (await client.get("/api/v1/users/me", headers=headers)).json()
    assert me["email"] == email and me["role"] == "admin"  # first user of a new org is its admin
    assert me["organization_name"] == "Test Co"

    renamed = await client.patch("/api/v1/users/me", headers=headers, json={"full_name": "Renamed Person"})
    assert renamed.json()["full_name"] == "Renamed Person"


async def test_wrong_password_is_rejected(client):
    response = await client.post("/api/v1/auth/login", json={"email": "agent@demo.talkwiseai.com", "password": "nope"})
    assert response.status_code == 401


async def test_change_password(client):
    email = _email()
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123", "full_name": "P"})
    headers = await login(client, email, "Password123")

    wrong = await client.post("/api/v1/users/me/password", headers=headers,
                              json={"current_password": "bad-password", "new_password": "Another123"})
    assert wrong.status_code == 400
    ok = await client.post("/api/v1/users/me/password", headers=headers,
                           json={"current_password": "Password123", "new_password": "Another123"})
    assert ok.status_code == 204
    await login(client, email, "Another123")


async def test_password_reset_flow(client):
    email = _email()
    await client.post("/api/v1/auth/register", json={"email": email, "password": "Password123", "full_name": "R"})

    # Same answer for unknown emails, so accounts can't be discovered
    unknown = await client.post("/api/v1/auth/forgot-password", json={"email": "nobody@example.com"})
    known = await client.post("/api/v1/auth/forgot-password", json={"email": email})
    assert unknown.json()["message"] == known.json()["message"]

    from sqlalchemy import select
    from app.db.models import User
    from app.db.session import AsyncSessionLocal

    async with AsyncSessionLocal() as db:
        user = (await db.execute(select(User).where(User.email == email))).scalar_one()
        token = create_password_reset_token(user.id, user.hashed_password)

    reset = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "BrandNew123"})
    assert reset.status_code == 204
    await login(client, email, "BrandNew123")

    # The token is tied to the old password, so it can't be used twice
    reused = await client.post("/api/v1/auth/reset-password", json={"token": token, "new_password": "Again12345"})
    assert reused.status_code == 400
    garbage = await client.post("/api/v1/auth/reset-password", json={"token": "not-a-token", "new_password": "Again12345"})
    assert garbage.status_code == 400


async def test_login_rate_limit(client, monkeypatch):
    from app.core import rate_limit
    from app.core.config import settings

    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    rate_limit.store.reset()
    try:
        codes = [
            (await client.post("/api/v1/auth/login", json={"email": "x@example.com", "password": "wrong"})).status_code
            for _ in range(rate_limit.AUTH_LIMIT + 1)
        ]
    finally:
        rate_limit.store.reset()
    assert codes[:-1] == [401] * rate_limit.AUTH_LIMIT
    assert codes[-1] == 429


async def test_admin_manages_team(client, admin):
    email = _email()
    created = await client.post("/api/v1/users", headers=admin, json={
        "email": email, "full_name": "Temp Agent", "role": "agent", "temporary_password": "Temporary123",
    })
    assert created.status_code == 201, created.text
    member = created.json()
    assert member["role"] == "agent" and member["is_active"]

    duplicate = await client.post("/api/v1/users", headers=admin, json={
        "email": email, "full_name": "Again", "role": "agent", "temporary_password": "Temporary123",
    })
    assert duplicate.status_code == 409

    promoted = await client.patch(f"/api/v1/users/{member['id']}/role", headers=admin, json={"role": "manager"})
    assert promoted.json()["role"] == "manager"

    deactivated = await client.patch(f"/api/v1/users/{member['id']}", headers=admin, json={"is_active": False})
    assert deactivated.json()["is_active"] is False
    blocked = await client.post("/api/v1/auth/login", json={"email": email, "password": "Temporary123"})
    assert blocked.status_code == 403

    team = (await client.get("/api/v1/users", headers=admin)).json()
    assert any(u["email"] == "agent@demo.talkwiseai.com" and u["conversation_count"] > 0 for u in team)


async def test_admin_cannot_lock_themselves_out(client, admin):
    me = (await client.get("/api/v1/users/me", headers=admin)).json()
    assert (await client.patch(f"/api/v1/users/{me['id']}", headers=admin, json={"is_active": False})).status_code == 400
    assert (await client.patch(f"/api/v1/users/{me['id']}/role", headers=admin, json={"role": "agent"})).status_code == 400


async def test_preferences_round_trip(client, agent2):
    defaults = (await client.get("/api/v1/users/me/preferences", headers=agent2)).json()
    assert defaults == {"auto_action_items": True, "lead_intent_alerts": True, "pbx_auto_sync": False}
    saved = await client.put("/api/v1/users/me/preferences", headers=agent2, json={"lead_intent_alerts": False})
    assert saved.json()["lead_intent_alerts"] is False
    assert (await client.get("/api/v1/users/me/preferences", headers=agent2)).json()["lead_intent_alerts"] is False
    await client.put("/api/v1/users/me/preferences", headers=agent2, json={"lead_intent_alerts": True})


async def test_rate_limited_responses_are_readable_by_the_browser(client, monkeypatch):
    """429s need CORS headers (or the web app sees a network error), and preflights don't count."""
    from app.core import rate_limit
    from app.core.config import settings

    origin = {"Origin": "http://localhost:3000"}
    monkeypatch.setattr(settings, "rate_limit_enabled", True)
    monkeypatch.setattr(settings, "rate_limit_requests", 3)
    rate_limit.store.reset()
    try:
        for _ in range(5):
            preflight = await client.options("/api/v1/integrations", headers={
                **origin, "Access-Control-Request-Method": "GET", "Access-Control-Request-Headers": "authorization",
            })
            assert preflight.status_code == 200
        codes = [(await client.get("/api/v1/integrations", headers=origin)).status_code for _ in range(4)]
        assert codes == [401, 401, 401, 429]  # unauthenticated, but still counted
        limited = await client.get("/api/v1/integrations", headers=origin)
        assert limited.status_code == 429
        assert limited.headers.get("access-control-allow-origin") == "http://localhost:3000"
        assert int(limited.headers["retry-after"]) >= 1
    finally:
        rate_limit.store.reset()
