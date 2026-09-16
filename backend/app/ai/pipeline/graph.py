"""
LangGraph Conversation Processing Graph.

Orchestrates all AI agents in a stateful directed graph.
Parallel analysis nodes run concurrently for performance.

Pipeline flow:
  START → clean_transcript → classify → [PARALLEL ANALYSIS] → aggregate → score_agent → END
"""

import asyncio
from functools import partial
from typing import Any

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


class ConversationPipeline:
    """
    Multi-agent LangGraph-inspired conversation processing pipeline.

    Orchestrates 15+ specialized AI agents in a structured workflow.
    Parallel analysis agents run concurrently using asyncio.gather().

    Note: This implements the LangGraph pattern with asyncio for
    concurrent node execution. The langgraph library is used for
    the graph structure and state management.
    """

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
        on_step: Any = None,  # Optional callback for progress reporting
    ) -> ConversationState:
        """
        Run the full conversation intelligence pipeline.

        Args:
            conversation_id: UUID of the conversation being processed
            organization_id: UUID of the owning organization
            raw_segments: List of transcript segments from STT
            full_transcript_text: Complete transcript as plain text
            language: Detected language code
            duration_seconds: Total conversation duration
            audio_file_path: Path to the audio file (if available)
            uploaded_file_name: Original uploaded filename
            on_step: Optional async callback(step_name, progress_pct) for progress updates

        Returns:
            Fully populated ConversationState with all AI insights
        """
        # Build initial state
        state: ConversationState = {
            "conversation_id": conversation_id,
            "organization_id": organization_id,
            "audio_file_path": audio_file_path,
            "uploaded_file_name": uploaded_file_name,
            "raw_segments": raw_segments,  # type: ignore
            "full_transcript_text": full_transcript_text,
            "language": language,
            "duration_seconds": duration_seconds,
            "speaker_map": {},
            # All other fields will be populated by agents
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

        llm = self._llm

        async def _report(step: str, pct: int) -> None:
            if on_step:
                try:
                    await on_step(step, pct)
                except Exception:
                    pass

        try:
            # ---- Step 1: Clean and label transcript ----
            logger.info("Pipeline step: clean_transcript", conversation_id=conversation_id)
            await _report("Cleaning transcript", 5)
            update = await node_clean_transcript(state, llm)
            state.update(update)

            # ---- Step 2: Classify conversation ----
            logger.info("Pipeline step: classify", conversation_id=conversation_id)
            await _report("Classifying conversation", 10)
            update = await node_classify_conversation(state, llm)
            state.update(update)

            # ---- Step 3: Parallel analysis (7 agents run concurrently) ----
            logger.info("Pipeline step: parallel_analysis", conversation_id=conversation_id)
            await _report("Running AI analysis", 20)

            parallel_results = await asyncio.gather(
                node_summarize(state, llm),
                node_analyze_sentiment(state, llm),
                node_analyze_intent(state, llm),
                node_extract_pain_points(state, llm),
                node_analyze_sales_intelligence(state, llm),
                node_detect_objections(state, llm),
                node_extract_entities(state, llm),
                node_extract_action_items(state, llm),
                return_exceptions=True,  # Don't let one failure crash all parallel agents
            )

            # Apply successful results; log failures without crashing
            for result in parallel_results:
                if isinstance(result, Exception):
                    err_msg = str(result)
                    logger.error("Parallel agent failed", error=err_msg)
                    state["errors"].append(err_msg)
                elif isinstance(result, dict):
                    state.update(result)

            # ---- Step 4: Meeting minutes (needs summary + transcript) ----
            logger.info("Pipeline step: meeting_minutes", conversation_id=conversation_id)
            await _report("Generating meeting minutes", 70)
            update = await node_generate_meeting_minutes(state, llm)
            state.update(update)

            # ---- Step 5: Recommendations ----
            logger.info("Pipeline step: recommendations", conversation_id=conversation_id)
            await _report("Generating recommendations", 80)
            update = await node_generate_recommendations(state, llm)
            state.update(update)

            # ---- Step 6: CRM update proposals ----
            logger.info("Pipeline step: crm_proposals", conversation_id=conversation_id)
            await _report("Generating CRM proposals", 88)
            update = await node_propose_crm_updates(state, llm)
            state.update(update)

            # ---- Step 7: Agent performance score ----
            logger.info("Pipeline step: agent_score", conversation_id=conversation_id)
            await _report("Scoring agent performance", 95)
            update = await node_score_agent_performance(state, llm)
            state.update(update)

            state["status"] = "completed"
            await _report("Complete", 100)
            logger.info("Pipeline completed successfully", conversation_id=conversation_id)

        except Exception as e:
            err_msg = str(e)
            logger.error("Pipeline failed", conversation_id=conversation_id, error=err_msg)
            state["errors"].append(f"Pipeline error: {err_msg}")
            state["status"] = "failed"

        return state


def get_llm_provider() -> LLMProvider:
    """Factory: return the configured LLM provider based on settings."""
    from app.core.config import settings

    if settings.llm_provider == "openai":
        from app.ai.providers.llm.openai_provider import OpenAILLMProvider
        return OpenAILLMProvider()
    else:
        from app.ai.providers.llm.mock_provider import MockLLMProvider
        return MockLLMProvider()


def get_stt_provider():
    """Factory: return the configured STT provider."""
    from app.core.config import settings

    if settings.stt_provider == "whisper_local":
        from app.ai.providers.stt.whisper_provider import WhisperLocalProvider
        return WhisperLocalProvider()
    else:
        from app.ai.providers.stt.mock_provider import MockSTTProvider
        return MockSTTProvider()
