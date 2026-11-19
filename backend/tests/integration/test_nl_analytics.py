"""Natural-language analytics through the Copilot endpoint (docs/SPEC.md §34 examples)."""

import pytest

SPEC_QUESTIONS = {
    "How many high-intent leads did we have this month?": "high_intent_leads",
    "Which objection appeared most frequently?": "top_objections",
    "What percentage of calls were positive?": "sentiment_breakdown",
    "Which sales representative had the highest average score?": "agent_leaderboard",
    "Which customers mentioned competitors?": "competitor_mentions",
}


async def ask(client, headers, question):
    response = await client.post("/api/v1/ai/copilot/chat", headers=headers, json={"query": question})
    assert response.status_code == 200, response.text
    return response.json()


@pytest.mark.parametrize("question, tool", SPEC_QUESTIONS.items())
async def test_spec_questions_use_predefined_analytics(client, admin, question, tool):
    body = await ask(client, admin, question)
    assert body["analytics"]["tool"] == tool
    assert body["answer"] and body["citations"] == []


async def test_sentiment_numbers_match_the_analytics_api(client, admin):
    body = await ask(client, admin, "What percentage of calls were positive?")
    overview = (await client.get("/api/v1/analytics/overview", headers=admin, params={"days": 30})).json()
    counts = {row[0]: row[1] for row in body["analytics"]["rows"]}
    assert counts == overview["sentiment_distribution"]
    total = sum(counts.values())
    assert f"{round(counts.get('positive', 0) / total * 100)}% of the {total}" in body["answer"]


async def test_top_n_and_type_filters(client, admin):
    body = await ask(client, admin, "What are the top two objections in sales calls this year?")
    assert body["analytics"]["tool"] == "top_objections"
    assert len(body["analytics"]["rows"]) <= 2
    assert body["analytics"]["period"] == "this year"


async def test_agents_only_get_their_own_ranking(client, agent):
    body = await ask(client, agent, "Which sales representative had the highest average score?")
    assert len(body["analytics"]["rows"]) == 1
    assert body["answer"].startswith("Your average QA score")


async def test_content_questions_fall_back_to_search(client, admin):
    body = await ask(client, admin, "What did customers say about integrations?")
    assert body["analytics"] is None


async def test_natural_language_query_endpoint(client, manager):
    response = await client.post("/api/v1/ai/natural-language-query", headers=manager,
                                 json={"query": "How many meetings did we have in the last 90 days?"})
    body = response.json()
    assert body["query_type"] == "conversation_volume"
    assert body["answer"].startswith("There were")
