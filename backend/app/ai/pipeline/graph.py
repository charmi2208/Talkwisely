"""
LangGraph Conversation Processing Graph.

The pipeline is a compiled LangGraph ``StateGraph`` over ``ConversationState``:

    START
      -> validate_input
      -> clean_transcript            (speaker labelling)
      -> classify
      -> summarize | sentiment | intent | pain_points |
         sales_intelligence | objections | entities | action_items   (parallel)
      -> aggregate                   (fan-in: waits for all eight)
      -> meeting_minutes
      -> crm_update
      -> recommendations
      -> agent_score                 (QA)
      -> END

The eight analysis agents run in the same superstep, so LangGraph executes them
concurrently. A failure in one of them is recorded in ``state["errors"]`` and the
others carry on. A failure in a sequential step marks the run ``failed`` and a
conditional edge routes straight to END, because later steps depend on it.

Nodes never touch the database. Storing results, embedding and indexing happen in
``app/workers/conversation_tasks.py`` after the graph returns.
"""

from contextlib import asynccontextmanager
from typing import Any, Awaitable, Callable

from langgraph.graph import END, START, StateGraph

from app.ai.pipeline.nodes import (
    node_analyze_intent,
    node_analyze_sales_intelligence,
    node_analyze_sentiment,
    node_clean_transcript,
    node_classify_conversation,
    node_detect_objections,
    node_extract_action_items,
    node_extract_entities,
    node_extract_pain_points,
    node_generate_meeting_minutes,
    node_generate_recommendations,
    node_propose_crm_updates,
    node_score_agent_performance,
    node_summarize,
)
from app.ai.pipeline.state import ConversationState
from app.ai.providers.base import LLMProvider
from app.core.logging import get_logger

logger = get_logger("pipeline.graph")

ProgressCallback = Callable[[str, int], Awaitable[None]]


class PipelineError(Exception):
    """The pipeline couldn't produce results. The message is safe to show to users."""


# Parallel analysis agents: graph node name -> node function
ANALYSIS_NODES: dict[str, Any] = {
    "summarize": node_summarize,
    "sentiment": node_analyze_sentiment,
    "intent": node_analyze_intent,
    "pain_points": node_extract_pain_points,
    "sales_intelligence": node_analyze_sales_intelligence,
    "objections": node_detect_objections,
    "entities": node_extract_entities,
    "action_items": node_extract_action_items,
}

# Steps after the fan-in, in order: (node name, node function, progress label, progress %)
POST_ANALYSIS_STEPS: list[tuple[str, Any, str, int]] = [
    ("meeting_minutes", node_generate_meeting_minutes, "Generating meeting minutes", 70),
    ("crm_update", node_propose_crm_updates, "Preparing CRM update proposals", 78),
    ("recommendations", node_generate_recommendations, "Generating recommendations", 86),
    ("agent_score", node_score_agent_performance, "Scoring agent performance", 94),
]

# Progress range covered while the parallel agents finish
_ANALYSIS_START_PCT = 20
_ANALYSIS_END_PCT = 65

NO_SPEECH_MESSAGE = "No speech was found in the recording, so there is nothing to analyze."


def node_validate_input(state: ConversationState) -> dict:
    """Stop early when speech-to-text produced nothing to analyze."""
    has_text = any((seg.get("text") or "").strip() for seg in state.get("raw_segments", []))
    if not has_text and not (state.get("full_transcript_text") or "").strip():
        return {"status": "failed", "errors": [NO_SPEECH_MESSAGE], "current_step": "validation_failed"}
    return {"current_step": "validated", "steps_completed": ["validate_input"]}


def _route_unless_failed(next_nodes: str | list[str]):
    """Conditional edge: continue to ``next_nodes`` unless a step marked the run failed."""
    def route(state: ConversationState):
        return END if state.get("status") == "failed" else next_nodes
    return route


def build_graph(llm: LLMProvider | None, report: ProgressCallback | None = None):
    """Compile the pipeline graph for one run.

    ``llm`` and ``report`` are bound into the node closures, so build a fresh graph per
    run (compiling this graph takes milliseconds). ``llm`` may be None when the graph is
    only built to draw it.
    """
    async def _report(step: str, pct: int) -> None:
        if report:
            try:
                await report(step, pct)
            except Exception:  # progress reporting must never break the pipeline
                pass

    def sequential(name: str, fn, label: str, pct: int):
        async def run(state: ConversationState) -> dict:
            await _report(label, pct)
            logger.info("Pipeline step", step=name, conversation_id=state.get("conversation_id"))
            try:
                return await fn(state, llm)
            except Exception as e:
                logger.error("Pipeline step failed", step=name, error=str(e))
                return {"status": "failed", "errors": [f"{name}: {e}"], "current_step": f"{name}_failed"}
        return run

    finished = 0

    def parallel(name: str, fn):
        async def run(state: ConversationState) -> dict:
            nonlocal finished
            try:
                update = await fn(state, llm)
            except Exception as e:
                logger.error("Analysis agent failed", agent=name, error=str(e))
                update = {"errors": [f"{name}: {e}"]}
            finished += 1
            span = _ANALYSIS_END_PCT - _ANALYSIS_START_PCT
            pct = _ANALYSIS_START_PCT + span * finished // len(ANALYSIS_NODES)
            await _report(f"AI analysis: {finished} of {len(ANALYSIS_NODES)} agents done", pct)
            return update
        return run

    async def aggregate(state: ConversationState) -> dict:
        errors = state.get("errors", [])
        if errors:
            logger.warning("Analysis finished with agent errors", count=len(errors))
        return {"current_step": "aggregated", "steps_completed": ["aggregate"]}

    async def validate(state: ConversationState) -> dict:
        await _report("Validating transcript", 2)
        return node_validate_input(state)

    graph = StateGraph(ConversationState)
    graph.add_node("validate_input", validate)
    graph.add_node("clean_transcript", sequential("clean_transcript", node_clean_transcript, "Cleaning transcript", 5))
    graph.add_node("classify", sequential("classify", node_classify_conversation, "Classifying conversation", 12))
    for name, fn in ANALYSIS_NODES.items():
        graph.add_node(name, parallel(name, fn))
    graph.add_node("aggregate", aggregate)
    for name, fn, label, pct in POST_ANALYSIS_STEPS:
        graph.add_node(name, sequential(name, fn, label, pct))

    analysis = list(ANALYSIS_NODES)
    graph.add_edge(START, "validate_input")
    graph.add_conditional_edges("validate_input", _route_unless_failed("clean_transcript"), ["clean_transcript", END])
    graph.add_conditional_edges("clean_transcript", _route_unless_failed("classify"), ["classify", END])
    graph.add_conditional_edges("classify", _route_unless_failed(analysis), [*analysis, END])
    graph.add_edge(analysis, "aggregate")  # fan-in: runs once all eight have finished

    previous = "aggregate"
    for name, *_ in POST_ANALYSIS_STEPS:
        if previous == "aggregate":
            graph.add_edge(previous, name)
        else:
            graph.add_conditional_edges(previous, _route_unless_failed(name), [name, END])
        previous = name
    graph.add_edge(previous, END)

    return graph.compile()


def pipeline_mermaid() -> str:
    """Mermaid source for the pipeline graph (used to keep the docs diagram current)."""
    return build_graph(llm=None).get_graph().draw_mermaid()


def initial_state(
    conversation_id: str,
    organization_id: str,
    raw_segments: list[dict],
    full_transcript_text: str,
    language: str,
    duration_seconds: float,
    audio_file_path: str | None = None,
    uploaded_file_name: str | None = None,
) -> ConversationState:
    """Empty pipeline state for one conversation; agents fill in the rest."""
    return {
        "conversation_id": conversation_id,
        "organization_id": organization_id,
        "audio_file_path": audio_file_path,
        "uploaded_file_name": uploaded_file_name,
        "raw_segments": raw_segments,  # type: ignore[typeddict-item]
        "full_transcript_text": full_transcript_text,
        "language": language,
        "duration_seconds": duration_seconds,
        "speaker_map": {},
        "conversation_type": "",
        "primary_purpose": "",
        "business_context": "",
        "classification_confidence": 0.0,
        "executive_summary": "",
        "detailed_summary": "",
        "key_topics": [],
        "decisions": [],
        "important_moments": [],
        "open_questions": [],
        "next_steps": [],
        "action_items": [],
        "overall_sentiment": "neutral",
        "overall_sentiment_score": 0.0,
        "customer_sentiment": "neutral",
        "agent_sentiment": "neutral",
        "sentiment_trend": "",
        "sentiment_timeline": [],
        "positive_moments": [],
        "negative_moments": [],
        "frustration_detected": False,
        "satisfaction_detected": False,
        "primary_intent": "",
        "secondary_intents": [],
        "intent_confidence": 0.0,
        "intent_evidence": [],
        "pain_points": [],
        "lead_score": None,
        "purchase_intent": None,
        "deal_health": None,
        "budget_discussed": False,
        "budget_range": None,
        "decision_maker_present": False,
        "timeline_discussed": False,
        "deal_timeline": None,
        "buying_signals": [],
        "upsell_opportunities": [],
        "cross_sell_opportunities": [],
        "pipeline_stage": None,
        "closing_probability": None,
        "objections": [],
        "entities": [],
        "meeting_minutes": None,
        "recommendations": [],
        "crm_proposed_changes": None,
        "agent_score": None,
        "generated_email": None,
        "current_step": "started",
        "steps_completed": [],
        "errors": [],
        "status": "processing",
    }


class ConversationPipeline:
    """Runs the LangGraph conversation intelligence graph for one conversation."""

    def __init__(self, llm: LLMProvider) -> None:
        self._llm = llm

    async def run(
        self,
        conversation_id: str,
        organization_id: str,
        raw_segments: list[dict],
        full_transcript_text: str,
        language: str,
        duration_seconds: float,
        audio_file_path: str | None = None,
        uploaded_file_name: str | None = None,
        on_step: ProgressCallback | None = None,
    ) -> ConversationState:
        """Run the full graph and return the final state.

        ``on_step(step_name, pct)`` is awaited as steps start (and as each parallel
        agent finishes) so callers can show progress. The returned state's ``status``
        is ``completed`` or ``failed``; ``errors`` lists what went wrong either way.
        """
        state = initial_state(
            conversation_id=conversation_id,
            organization_id=organization_id,
            raw_segments=raw_segments,
            full_transcript_text=full_transcript_text,
            language=language,
            duration_seconds=duration_seconds,
            audio_file_path=audio_file_path,
            uploaded_file_name=uploaded_file_name,
        )
        app = build_graph(self._llm, on_step)

        try:
            result: ConversationState = await app.ainvoke(state)
        except Exception as e:  # node wrappers catch agent errors; this is LangGraph itself
            logger.error("Pipeline graph failed", conversation_id=conversation_id, error=str(e))
            state["errors"].append(f"Pipeline error: {e}")
            state["status"] = "failed"
            return state

        if result.get("status") != "failed":
            result["status"] = "completed"
            if on_step:
                try:
                    await on_step("Complete", 100)
                except Exception:
                    pass
            logger.info("Pipeline completed", conversation_id=conversation_id, errors=len(result.get("errors", [])))
        else:
            logger.error("Pipeline stopped", conversation_id=conversation_id, errors=result.get("errors"))
        return result


def get_llm_provider() -> LLMProvider:
    """Factory: return the configured LLM provider based on settings."""
    from app.core.config import settings

    if settings.llm_provider == "openai":
        from app.ai.providers.llm.openai_provider import OpenAILLMProvider
        return OpenAILLMProvider()
    else:
        from app.ai.providers.llm.mock_provider import MockLLMProvider
        return MockLLMProvider()


@asynccontextmanager
async def llm_session():
    """Yield the configured LLM provider and close its HTTP client afterwards."""
    llm = get_llm_provider()
    try:
        yield llm
    finally:
        close = getattr(llm, "aclose", None)
        if close:
            await close()


def get_stt_provider():
    """Factory: return the configured STT provider."""
    from app.core.config import settings

    if settings.stt_provider == "whisper_local":
        from app.ai.providers.stt.whisper_provider import WhisperLocalProvider
        return WhisperLocalProvider()
    if settings.stt_provider == "whisper_api":
        from app.ai.providers.stt.whisper_api_provider import WhisperAPIProvider
        return WhisperAPIProvider()
    else:
        from app.ai.providers.stt.mock_provider import MockSTTProvider
        return MockSTTProvider()
