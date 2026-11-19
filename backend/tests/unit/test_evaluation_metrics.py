"""Metric functions used by evaluation/run_eval.py, plus a mock-mode smoke run."""

import json

import pytest

from evaluation.run_eval import (
    DATASET, Counts, evaluate, has_keywords, match_keyword_items, match_sets, names_match,
)


def test_match_sets_counts_each_item_once():
    assert match_sets(["price", "price", "timing"], ["price", "security"]) == (1, 2, 1)


def test_precision_recall_f1():
    c = Counts()
    c.add(tp=3, fp=1, fn=2)
    assert c.precision == pytest.approx(0.75)
    assert c.recall == pytest.approx(0.6)
    assert c.f1 == pytest.approx(2 * 0.75 * 0.6 / 1.35)
    assert Counts().f1 is None


def test_competitor_names_match_loosely():
    assert names_match("Zoom Phone", "Zoom")
    assert names_match("ringcentral", "RingCentral")
    assert not names_match("Vonage", "8x8")


def test_keyword_matching_for_action_items():
    assert has_keywords("I'll call you back tomorrow", ["call", "back"])
    assert match_keyword_items(["Send revised quote", "Book a lunch"], [["quote"], ["demo"]]) == (1, 1, 1)


def test_dataset_is_well_formed():
    examples = json.loads(DATASET.read_text())["examples"]
    assert len(examples) >= 6
    for example in examples:
        assert {"conversation_type", "overall_sentiment", "primary_intent", "objection_categories",
                "competitors", "action_items", "summary_facts"} <= set(example["expected"])


async def test_mock_smoke_run():
    from app.ai.providers.llm.mock_provider import MockLLMProvider

    examples = json.loads(DATASET.read_text())["examples"][:2]
    run = await evaluate(examples, MockLLMProvider())
    metrics = run["metrics"]
    assert metrics["pipeline_completed"] == 2
    assert metrics["structured_output_validity"] == 1.0  # canned responses match every schema
    assert metrics["agent_responses"] == 2 * 13
