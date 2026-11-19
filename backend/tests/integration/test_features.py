"""Analytics, action items, sales pipeline, meetings, integrations, reports, knowledge base."""

from datetime import date, timedelta

from tests.conftest import upload


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------

async def test_analytics_overview_is_consistent(client, admin):
    overview = (await client.get("/api/v1/analytics/overview", params={"days": 365}, headers=admin)).json()
    assert overview["total_conversations"] == overview["total_calls"] + overview["total_meetings"]
    assert overview["total_conversations"] >= overview["completed_conversations"] > 0
    assert sum(overview["conversations_by_type"].values()) == overview["total_conversations"]
    assert 0 <= overview["average_agent_score"] <= 100
    assert set(overview["changes"]) == {
        "total_conversations_pct", "high_intent_leads_pct", "average_agent_score_points", "average_sentiment_score_points",
    }


async def test_analytics_trends_cover_every_day(client, admin):
    trend = (await client.get("/api/v1/analytics/conversations", params={"days": 14}, headers=admin)).json()
    assert len(trend["data"]) == 14
    assert trend["data"][-1]["date"] == date.today().isoformat()
    assert all(d["total"] == d["calls"] + d["meetings"] for d in trend["data"])


async def test_analytics_filters(client, admin):
    everything = (await client.get("/api/v1/analytics/overview", params={"days": 365}, headers=admin)).json()
    sales_only = (await client.get(
        "/api/v1/analytics/overview", params={"days": 365, "conversation_type": "sales"}, headers=admin
    )).json()
    assert sales_only["total_conversations"] == everything["conversations_by_type"].get("sales", 0)

    board = (await client.get("/api/v1/analytics/agents", params={"days": 365}, headers=admin)).json()
    person = board["leaderboard"][0]
    mine = (await client.get(
        "/api/v1/analytics/agents", params={"days": 365, "agent_id": person["user_id"]}, headers=admin
    )).json()
    assert [p["user_id"] for p in mine["leaderboard"]] == [person["user_id"]]


async def test_other_analytics_endpoints(client, admin):
    for path in ("sentiment", "objections", "sales", "topics"):
        response = await client.get(f"/api/v1/analytics/{path}", params={"days": 365}, headers=admin)
        assert response.status_code == 200, (path, response.text)
    objections = (await client.get("/api/v1/analytics/objections", params={"days": 365}, headers=admin)).json()["data"]
    assert objections and all(0 <= o["resolution_rate"] <= 1 for o in objections)


# ---------------------------------------------------------------------------
# Action items
# ---------------------------------------------------------------------------

async def test_manual_action_item_without_conversation(client, agent, agent2):
    """Regression: tasks added on the Action Items page have no conversation."""
    created = await client.post("/api/v1/action-items", headers=agent, json={"description": "Prepare QBR deck", "owner": "Me"})
    assert created.status_code == 201, created.text
    item = created.json()
    assert item["conversation_id"] is None and item["is_ai_generated"] is False

    mine = {i["id"] for i in (await client.get("/api/v1/action-items", headers=agent)).json()}
    theirs = {i["id"] for i in (await client.get("/api/v1/action-items", headers=agent2)).json()}
    assert item["id"] in mine and item["id"] not in theirs

    done = await client.patch(f"/api/v1/action-items/{item['id']}", headers=agent, json={"status": "completed"})
    assert done.json()["status"] == "completed" and done.json()["completed_at"]
    assert (await client.delete(f"/api/v1/action-items/{item['id']}", headers=agent)).status_code == 204


async def test_past_due_tasks_become_overdue(client, agent):
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    item = (await client.post("/api/v1/action-items", headers=agent,
                              json={"description": "Late task", "due_date": yesterday})).json()
    assert item["status"] == "overdue"
    moved = await client.patch(f"/api/v1/action-items/{item['id']}", headers=agent,
                               json={"due_date": (date.today() + timedelta(days=3)).isoformat()})
    assert moved.json()["status"] == "pending"
    bad = await client.patch(f"/api/v1/action-items/{item['id']}", headers=agent, json={"priority": "whenever"})
    assert bad.status_code == 422
    await client.delete(f"/api/v1/action-items/{item['id']}", headers=agent)


async def test_auto_action_items_preference(client, agent2):
    await client.put("/api/v1/users/me/preferences", headers=agent2, json={"auto_action_items": False})
    try:
        conversation_id = await upload(client, agent2, "No automatic tasks please")
        insights = (await client.get(f"/api/v1/conversations/{conversation_id}/insights", headers=agent2)).json()
        assert insights["action_items"] == []
        assert insights["summary"]  # the rest of the analysis still ran
    finally:
        await client.put("/api/v1/users/me/preferences", headers=agent2, json={"auto_action_items": True})
    await client.delete(f"/api/v1/conversations/{conversation_id}", headers=agent2)


# ---------------------------------------------------------------------------
# Sales pipeline and meetings
# ---------------------------------------------------------------------------

async def test_sales_pipeline_and_stage_override(client, manager):
    leads = (await client.get("/api/v1/sales/pipeline", headers=manager)).json()
    assert leads
    lead = leads[0]
    assert {"next_action", "last_activity_at", "owner_name"} <= set(lead)

    moved = await client.patch(f"/api/v1/sales/leads/{lead['conversation_id']}", headers=manager, json={"stage": "negotiation"})
    assert moved.status_code == 200 and moved.json()["pipeline_stage"] == "negotiation"
    assert (await client.patch(f"/api/v1/sales/leads/{lead['conversation_id']}", headers=manager,
                               json={"stage": "maybe"})).status_code == 400

    only = (await client.get("/api/v1/sales/pipeline", params={"stage": "negotiation"}, headers=manager)).json()
    assert all(item["pipeline_stage"] == "negotiation" for item in only)


async def test_meetings_list_and_minutes(client, manager):
    meetings = (await client.get("/api/v1/meetings", headers=manager)).json()
    assert meetings
    minutes = await client.get(f"/api/v1/meetings/{meetings[0]['conversation_id']}/minutes", headers=manager)
    assert minutes.status_code == 200
    assert minutes.json()["formatted_markdown"]
    only_meetings = (await client.get("/api/v1/meetings", params={"meetings_only": True}, headers=manager)).json()
    assert all(m["conversation_type"] in ("internal_meeting", "client_meeting", "meeting") for m in only_meetings)


# ---------------------------------------------------------------------------
# Integrations
# ---------------------------------------------------------------------------

async def test_integrations_are_honest_about_mocks(client, admin):
    integrations = (await client.get("/api/v1/integrations", headers=admin)).json()
    assert {i["key"] for i in integrations} == {"talkwisely", "meetings", "crm", "calendar", "email"}
    assert all(i["is_mock"] for i in integrations)
    test = (await client.post("/api/v1/integrations/crm/test", headers=admin)).json()
    assert test["ok"] and "mock" in test["message"].lower()


async def test_integration_settings_validation(client, admin):
    bad = await client.put("/api/v1/integrations/talkwisely", headers=admin, json={"config": {"import_limit": 500}})
    assert bad.status_code == 422
    unavailable = await client.put("/api/v1/integrations/crm", headers=admin, json={"provider": "hubspot"})
    assert unavailable.status_code == 400
    ok = await client.put("/api/v1/integrations/crm", headers=admin, json={"config": {"crm_name": "HubSpot"}})
    assert ok.json()["config"]["crm_name"] == "HubSpot"


async def test_disabled_crm_blocks_approval(client, admin, agent):
    conversation_id = await upload(client, agent, "CRM switched off")
    proposal = (await client.get("/api/v1/crm/proposals", headers=agent, params={"conversation_id": conversation_id})).json()[0]

    await client.put("/api/v1/integrations/crm", headers=admin, json={"is_enabled": False})
    try:
        blocked = await client.post(f"/api/v1/crm/proposals/{proposal['id']}/approve", headers=agent, json={})
        assert blocked.status_code == 409
    finally:
        await client.put("/api/v1/integrations/crm", headers=admin, json={"is_enabled": True})
    rejected = await client.post(f"/api/v1/crm/proposals/{proposal['id']}/reject", headers=agent)
    assert rejected.json()["status"] == "rejected"
    await client.delete(f"/api/v1/conversations/{conversation_id}", headers=agent)


async def test_pbx_sync_imports_new_calls_once(client, manager):
    first = await client.post("/api/v1/integrations/talkwisely/sync", headers=manager)
    assert first.status_code == 200, first.text
    assert first.json()["imported"] == 2
    second = (await client.post("/api/v1/integrations/talkwisely/sync", headers=manager)).json()
    assert second["imported"] == 0 and second["skipped"] == 2

    imported = first.json()["conversation_ids"][0]
    detail = (await client.get(f"/api/v1/conversations/{imported}", headers=manager)).json()
    assert detail["status"] == "completed"


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------

async def test_reports_are_saved_and_downloadable(client, manager):
    generated = await client.post("/api/v1/reports/generate", headers=manager,
                                  json={"report_type": "team_qa", "time_period": "quarterly"})
    assert generated.status_code == 200, generated.text
    report = generated.json()
    assert report["id"] and report["title"].startswith("Agent Performance Report")

    listed = (await client.get("/api/v1/reports", headers=manager)).json()
    assert report["id"] in {r["id"] for r in listed}

    pdf = await client.get(f"/api/v1/reports/{report['id']}/download", params={"format": "pdf"}, headers=manager)
    assert pdf.status_code == 200 and pdf.content.startswith(b"%PDF")
    csv_file = await client.get(f"/api/v1/reports/{report['id']}/download", params={"format": "csv"}, headers=manager)
    assert csv_file.headers["content-type"].startswith("text/csv") and "Metric,Value" in csv_file.text
    md = await client.get(f"/api/v1/reports/{report['id']}/download", params={"format": "md"}, headers=manager)
    assert md.text.startswith("# Agent Performance Report")

    invalid = await client.post("/api/v1/reports/generate", headers=manager, json={"report_type": "astrology"})
    assert invalid.status_code == 422


async def test_conversation_csv_export(client, agent):
    export = await client.get("/api/v1/reports/export/csv", headers=agent)
    assert export.status_code == 200
    assert export.text.splitlines()[0].startswith("Conversation ID,Title")


# ---------------------------------------------------------------------------
# Knowledge base
# ---------------------------------------------------------------------------

async def test_knowledge_base_upload_and_delete(client, admin, agent):
    uploaded = await client.post(
        "/api/v1/knowledge-base/upload", headers=admin,
        files={"file": ("pricing.txt", b"Enterprise plan costs 40 dollars per seat per month.", "text/plain")},
        data={"title": "Pricing sheet", "category": "pricing"},
    )
    assert uploaded.status_code == 201, uploaded.text
    doc = uploaded.json()
    assert doc["category"] == "pricing" and doc["chunk_count"] == 1

    visible = (await client.get("/api/v1/knowledge-base", headers=agent)).json()
    assert doc["id"] in {d["id"] for d in visible}  # everyone can read it

    assert (await client.delete(f"/api/v1/knowledge-base/{doc['id']}", headers=admin)).status_code == 204


async def test_audit_log_records_actions(client, admin):
    logs = (await client.get("/api/v1/system/audit-logs", headers=admin, params={"limit": 200})).json()
    actions = {log["action"] for log in logs}
    assert {"login", "upload"} <= actions


async def test_analytics_are_cached_and_invalidated_by_new_data(client, agent2, monkeypatch):
    import app.api.v1.analytics as analytics_module

    computed = []
    original = analytics_module.get_or_compute

    async def spy(namespace, org, scope, params, compute, ttl=None):
        async def counting():
            computed.append(namespace)
            return await compute()
        return await original(namespace, org, scope, params, counting, ttl)

    monkeypatch.setattr(analytics_module, "get_or_compute", spy)
    params = {"days": 365}
    before = (await client.get("/api/v1/analytics/overview", headers=agent2, params=params)).json()
    again = (await client.get("/api/v1/analytics/overview", headers=agent2, params=params)).json()
    assert again == before
    assert computed.count("analytics:overview") == 1  # second request was a cache hit

    conversation_id = await upload(client, agent2, "Cache invalidation check")
    after = (await client.get("/api/v1/analytics/overview", headers=agent2, params=params)).json()
    assert after["total_conversations"] == before["total_conversations"] + 1
    await client.delete(f"/api/v1/conversations/{conversation_id}", headers=agent2)
    final = (await client.get("/api/v1/analytics/overview", headers=agent2, params=params)).json()
    assert final["total_conversations"] == before["total_conversations"]


async def test_meeting_recordings_import_once(client, manager, agent):
    first = await client.post("/api/v1/integrations/meetings/sync", headers=manager)
    assert first.status_code == 200, first.text
    assert first.json()["imported"] == 2
    again = (await client.post("/api/v1/integrations/meetings/sync", headers=manager)).json()
    assert again["imported"] == 0 and again["skipped"] == 2

    meetings = (await client.get("/api/v1/conversations", headers=manager, params={"search": "meeting:"})).json()["items"]
    titles = {m["title"] for m in meetings}
    assert "Zoom meeting: Quarterly business review with Northwind" in titles
    assert "Teams meeting: Weekly support stand-up" in titles

    assert (await client.post("/api/v1/integrations/meetings/sync", headers=agent)).status_code == 403
    assert (await client.post("/api/v1/integrations/crm/sync", headers=manager)).status_code == 400
    test = (await client.post("/api/v1/integrations/meetings/test", headers=manager)).json()
    assert test["ok"]
