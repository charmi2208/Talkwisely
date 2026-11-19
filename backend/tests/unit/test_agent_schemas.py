"""Structured output validation for agent responses."""

import pytest

from app.ai.providers.llm.mock_provider import MockLLMProvider
from app.ai.schemas.agent_outputs import AI_DISCLAIMER, SCHEMAS, validate_output


async def test_mock_responses_match_every_schema():
    llm = MockLLMProvider()
    for task in SCHEMAS:
        _, issues = validate_output(task, await llm.complete_json([], task=task))
        assert issues == [], (task, issues)


def test_common_model_mistakes_are_repaired_and_reported():
    clean, issues = validate_output("sales_intelligence", {
        "lead_score": "85/100", "purchase_intent": "High", "stage": "Proposal",
        "closing_probability": 70, "budget_range": "Not discussed", "decision_maker_present": "yes",
    })
    assert clean["lead_score"] == 85
    assert clean["purchase_intent"] == "high"
    assert clean["stage"] == "proposal"
    assert clean["closing_probability"] == pytest.approx(0.7)
    assert clean["budget_range"] is None  # "unknown" phrases become null, never a guess
    assert clean["decision_maker_present"] is True
    assert len(issues) == 5


def test_clock_timestamps_are_converted():
    clean, _ = validate_output("objections", {"objections": [
        {"category": "Price", "description": "Too expensive", "timestamp": "01:23", "severity": "HIGH"},
    ]})
    objection = clean["objections"][0]
    assert objection["timestamp"] == 83.0 and objection["category"] == "price" and objection["severity"] == "high"


def test_out_of_range_and_invalid_values():
    clean, issues = validate_output("agent_score", {"overall_score": 140, "empathy_score": "great"})
    assert clean["overall_score"] == 100
    assert clean["empathy_score"] is None
    assert clean["disclaimer"] == AI_DISCLAIMER  # QA scores are always labelled as AI assessments
    assert issues


def test_unknown_enum_values_fall_back_to_defaults():
    clean, issues = validate_output("classification", {"conversation_type": "podcast"})
    assert clean["conversation_type"] == "other"
    assert any("podcast" in i for i in issues)


def test_items_without_content_are_dropped():
    clean, _ = validate_output("action_items", {"action_items": [{"description": ""}, {"description": "Send deck"}, "junk"]})
    assert [i["description"] for i in clean["action_items"]] == ["Send deck"]


def test_non_object_and_missing_fields():
    clean, issues = validate_output("summarization", ["not", "an", "object"])
    assert clean["executive_summary"] == "" and clean["key_topics"] == []
    assert any("missing required field" in i for i in issues)


def test_crm_changes_need_from_and_to():
    clean, issues = validate_output("crm_update", {"proposed_changes": {"stage": {"from": "new", "to": "demo"}, "notes": "call back"}})
    assert clean["proposed_changes"]["stage"] == {"from": "new", "to": "demo"}
    assert clean["proposed_changes"]["notes"] == {"from": None, "to": "call back"}
    assert issues


def test_tasks_without_schema_pass_through():
    assert validate_output("email", {"subject": "Hi"}) == ({"subject": "Hi"}, [])
