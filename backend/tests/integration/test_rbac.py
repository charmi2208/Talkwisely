"""Role-based access: what admins, managers and agents may see and do."""

from tests.conftest import upload


async def test_agent_cannot_use_admin_endpoints(client, agent):
    assert (await client.get("/api/v1/users", headers=agent)).status_code == 403
    assert (await client.post("/api/v1/users", headers=agent, json={
        "email": "x@example.com", "full_name": "X", "role": "agent", "temporary_password": "Password123",
    })).status_code == 403
    assert (await client.put("/api/v1/integrations/crm", headers=agent, json={"is_enabled": False})).status_code == 403
    assert (await client.post("/api/v1/reports/generate", headers=agent, json={})).status_code == 403
    assert (await client.get("/api/v1/system/audit-logs", headers=agent)).status_code == 403
    kb = await client.post(
        "/api/v1/knowledge-base/upload", headers=agent,
        files={"file": ("a.txt", b"hello", "text/plain")}, data={"title": "A"},
    )
    assert kb.status_code == 403


async def test_manager_can_view_team_but_not_manage_it(client, manager):
    assert (await client.get("/api/v1/users", headers=manager)).status_code == 200
    assert (await client.put("/api/v1/integrations/crm", headers=manager, json={"is_enabled": True})).status_code == 403
    assert (await client.get("/api/v1/system/ai-settings", headers=manager)).status_code == 200


async def test_agents_only_see_their_own_conversations(client, admin, agent, agent2):
    own = await upload(client, agent2, "Agent two private call")

    def ids(response):
        return {c["id"] for c in response.json()["items"]}

    agent1_list = await client.get("/api/v1/conversations", params={"page_size": 100}, headers=agent)
    agent2_list = await client.get("/api/v1/conversations", params={"page_size": 100}, headers=agent2)
    admin_list = await client.get("/api/v1/conversations", params={"page_size": 100}, headers=admin)

    assert own in ids(agent2_list)
    assert own not in ids(agent1_list)
    assert own in ids(admin_list)
    assert ids(agent1_list) | ids(agent2_list) <= ids(admin_list)

    # Direct access is refused too, not just hidden from the list
    assert (await client.get(f"/api/v1/conversations/{own}", headers=agent)).status_code == 404
    assert (await client.get(f"/api/v1/conversations/{own}/insights", headers=agent)).status_code == 404
    assert (await client.post("/api/v1/ai/copilot/chat", headers=agent,
                              json={"query": "summary?", "conversation_id": own})).status_code == 404

    # Leaderboard: agents see only themselves; managers see everyone
    agent_board = (await client.get("/api/v1/analytics/agents", params={"days": 365}, headers=agent)).json()
    admin_board = (await client.get("/api/v1/analytics/agents", params={"days": 365}, headers=admin)).json()
    assert len(agent_board["leaderboard"]) <= 1
    assert len(admin_board["leaderboard"]) >= 2

    await client.delete(f"/api/v1/conversations/{own}", headers=agent2)
