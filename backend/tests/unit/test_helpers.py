"""Small helpers: value coercion, roles, rate limiting, preferences, exports, mock routing."""

from types import SimpleNamespace

import pytest

from app.ai.providers.llm.mock_provider import MockLLMProvider
from app.core.access import is_privileged, primary_role
from app.core.preferences import DEFAULT_PREFERENCES, effective_preferences
from app.core.rate_limit import MemoryRateLimitStore
from app.db.sanitize import to_bool, to_float, to_int
from app.services.report_export import report_csv, report_pdf


@pytest.mark.parametrize("value, expected", [
    ("00:48", 48.0), ("1:02:03", 3723.0), ("85%", 0.85), ("12.5", 12.5), (7, 7.0), (None, None), ("n/a", None),
])
def test_to_float(value, expected):
    assert to_float(value) == expected


def test_to_int_and_bool():
    assert to_int("85/100") == 85
    assert to_int("7.6") == 8
    assert to_bool("Yes") is True and to_bool("no") is False


def _user(*roles):
    return SimpleNamespace(user_roles=[SimpleNamespace(role=SimpleNamespace(name=r)) for r in roles])


def test_primary_role_prefers_highest_privilege():
    assert primary_role(_user("agent", "admin")) == "admin"
    assert primary_role(_user("manager")) == "manager"
    assert primary_role(_user()) == "agent"
    assert is_privileged(_user("manager")) and not is_privileged(_user("agent"))


def test_rate_limit_store_window():
    store = MemoryRateLimitStore()
    assert [store.hit("ip", 3, 60) for _ in range(3)] == [None, None, None]
    assert store.hit("ip", 3, 60) > 0
    assert store.hit("other-ip", 3, 60) is None


def test_effective_preferences():
    assert effective_preferences(None) == DEFAULT_PREFERENCES
    prefs = effective_preferences({"pbx_auto_sync": True, "junk": True, "lead_intent_alerts": "yes"})
    assert prefs["pbx_auto_sync"] is True and "junk" not in prefs
    assert prefs["lead_intent_alerts"] is True  # non-boolean values are ignored, default kept


def test_report_exports():
    pdf = report_pdf("Weekly — Report", "# Title\n\nSummary with “quotes”.\n\n## Insights\n- one\n- two")
    assert pdf.startswith(b"%PDF")
    csv_text = report_csv("T", {"total": 3, "by_type": {"sales": 2}}, {"Insights": ["a"]})
    assert "by_type.sales,2" in csv_text and "Insights" in csv_text


async def test_mock_routes_by_task_not_prompt_keywords():
    """The QA prompt mentions 'objection_handling_score'; it must still get QA data."""
    llm = MockLLMProvider()
    score = await llm.complete_json([], task="agent_score")
    assert "overall_score" in score and "objections" not in score
    sales = await llm.complete_json([], task="sales_intelligence")
    assert "lead_score" in sales
