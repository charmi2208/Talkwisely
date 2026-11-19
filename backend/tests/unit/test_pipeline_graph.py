"""The LangGraph pipeline: ordering, parallelism, failure handling."""

import asyncio

import pytest

from app.ai.pipeline import graph as graph_module
from app.ai.pipeline.graph import ANALYSIS_NODES, NO_SPEECH_MESSAGE, ConversationPipeline, pipeline_mermaid
from app.ai.providers.llm.mock_provider import MockLLMProvider

SEGMENTS = [
    {"speaker": "SPEAKER_00", "start": 0.0, "end": 4.0, "text": "Hi, thanks for joining.", "confidence": 0.9},
    {"speaker": "SPEAKER_01", "start": 4.0, "end": 9.0, "text": "We need pricing for 200 seats.", "confidence": 0.9},
]


async def _run(llm=None, segments=SEGMENTS, on_step=None):
    return await ConversationPipeline(llm or MockLLMProvider()).run(
        conversation_id="c1", organization_id="o1", raw_segments=[dict(s) for s in segments],
        full_transcript_text=" ".join(s["text"] for s in segments), language="en",
        duration_seconds=9.0, on_step=on_step,
    )


async def test_full_run_completes_every_step():
    state = await _run()
    assert state["status"] == "completed"
    assert state["errors"] == []
    assert set(state["steps_completed"]) == {
        "validate_input", "clean_transcript", "classify", "aggregate", "meeting_minutes", "crm_update",
        "recommendations", "agent_score", "summarize", "sentiment", "intent", "pain_points",
        "sales_intelligence", "objections", "entities", "action_items",
    }
    # Fan-in: aggregate only runs after all eight analysis agents
    steps = state["steps_completed"]
    assert steps.index("aggregate") > max(steps.index(s) for s in ("summarize", "objections", "action_items"))
    assert state["lead_score"] is not None and state["recommendations"] and state["agent_score"]


async def test_progress_is_reported_in_order():
    seen = []

    async def on_step(name, pct):
        seen.append(pct)

    await _run(on_step=on_step)
    assert seen == sorted(seen) and seen[-1] == 100


async def test_analysis_agents_run_concurrently(monkeypatch):
    """Eight agents that each take 0.2 s should finish in well under 8 x 0.2 s."""
    async def slow(state, llm):
        await asyncio.sleep(0.2)
        return {}

    for name in ANALYSIS_NODES:
        monkeypatch.setitem(ANALYSIS_NODES, name, slow)
    started = asyncio.get_running_loop().time()
    state = await _run()
    assert state["status"] == "completed"
    assert asyncio.get_running_loop().time() - started < 1.0


async def test_failed_analysis_agent_does_not_stop_the_others(monkeypatch):
    async def broken(state, llm):
        raise RuntimeError("objection model exploded")

    monkeypatch.setitem(ANALYSIS_NODES, "objections", broken)
    state = await _run()
    assert state["status"] == "completed"
    assert any("objection model exploded" in e for e in state["errors"])
    assert state["executive_summary"]  # other agents' results are kept


async def test_failed_sequential_step_stops_the_run(monkeypatch):
    async def broken(state, llm):
        raise RuntimeError("classifier down")

    monkeypatch.setattr(graph_module, "node_classify_conversation", broken)
    state = await _run()
    assert state["status"] == "failed"
    assert "summarize" not in state["steps_completed"]


async def test_empty_transcript_fails_validation():
    state = await _run(segments=[])
    assert state["status"] == "failed"
    assert state["errors"] == [NO_SPEECH_MESSAGE]


def test_graph_diagram_lists_every_node():
    diagram = pipeline_mermaid()
    for node in ["validate_input", "classify", "aggregate", "agent_score", *ANALYSIS_NODES]:
        assert node in diagram
