"""Question routing and period parsing for natural-language analytics."""

from datetime import datetime

from app.services.nl_analytics import parse_period, route_by_rules, route_with_llm

NOW = datetime(2026, 11, 20, 10, 30)  # a Friday


def test_periods():
    assert parse_period("this month", NOW).start == datetime(2026, 11, 1)
    last_month = parse_period("last month", NOW)
    assert (last_month.start, last_month.end) == (datetime(2026, 10, 1), datetime(2026, 11, 1))
    assert parse_period("this week", NOW).start == datetime(2026, 11, 16)
    assert parse_period("in the last 2 weeks", NOW).label == "the last 14 days"
    assert parse_period("overall", NOW).start is None
    assert parse_period("anything else", NOW).key == "last_30_days"


def test_rules_need_an_analytic_cue_for_ambiguous_topics():
    assert route_by_rules("What objections did Acme raise?") is None
    assert route_by_rules("Which objection came up most often?").tool == "top_objections"
    assert route_by_rules("What was the sentiment of the BlueSky call?") is None
    assert route_by_rules("Summarize the main action items from recent meetings") is None


def test_limits_and_types():
    call = route_by_rules("top five objections in support calls")
    assert (call.tool, call.limit, call.types) == ("top_objections", 5, ("customer_support",))


class FakeLLM:
    provider_name = "fake"

    def __init__(self, reply):
        self.reply = reply

    async def complete_json(self, messages, task=None):
        assert task == "analytics_router"
        return self.reply


async def test_llm_routing_is_validated():
    ok = await route_with_llm("Ratio of won deals?", FakeLLM({"tool": "pipeline_stages", "period": "this_quarter"}), NOW)
    assert ok.tool == "pipeline_stages" and ok.period.key == "this_quarter" and ok.routed_by == "llm"
    # Names outside the closed lists are rejected, so the model can't invent a query
    assert await route_with_llm("x", FakeLLM({"tool": "DROP TABLE users"}), NOW) is None
    assert await route_with_llm("x", FakeLLM({"tool": "top_objections", "period": "since 1990"}), NOW) is None
    assert await route_with_llm("What did Dana say?", FakeLLM({"tool": None}), NOW) is None
