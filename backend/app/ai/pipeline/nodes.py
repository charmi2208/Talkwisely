"""
LangGraph Node Functions — one node per AI agent step.

Each node:
1. Reads from ConversationState
2. Calls the appropriate agent
3. Returns a dict with the updated state fields

Nodes are pure functions (no side effects) — database writes happen
after the graph completes.
"""

import asyncio
from typing import Any

from app.ai.pipeline.state import ConversationState
from app.ai.providers.base import LLMMessage, LLMProvider
from app.core.logging import get_logger

logger = get_logger("pipeline.nodes")


# ---------------------------------------------------------------------------
# Utility: Build transcript context string from segments
# ---------------------------------------------------------------------------

def _build_transcript_context(state: ConversationState, max_chars: int = 12000) -> str:
    """Format transcript segments into a clean string for LLM prompts."""
    lines = []
    for seg in state.get("raw_segments", []):
        speaker = seg.get("speaker_label", seg.get("speaker", "Speaker"))
        start = seg.get("start", 0)
        m, s = divmod(int(start), 60)
        timestamp = f"{m:02d}:{s:02d}"
        lines.append(f"[{timestamp}] {speaker}: {seg.get('text', '')}")
    result = "\n".join(lines)
    return result[:max_chars] if len(result) > max_chars else result


async def _safe_call_agent(
    llm: LLMProvider,
    system_prompt: str,
    user_content: str,
    agent_name: str,
) -> dict:
    """Call LLM safely, returning {} on failure instead of crashing the pipeline."""
    try:
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_content),
        ]
        return await llm.complete_json(messages)
    except Exception as e:
        logger.error(f"Agent {agent_name} failed", error=str(e))
        return {}


# ---------------------------------------------------------------------------
# Node: Clean and validate transcript
# ---------------------------------------------------------------------------

MAX_ATTRIBUTION_SEGMENTS = 150


async def _attribute_speaker_roles(llm: LLMProvider, segments: list[dict]) -> dict[int, str]:
    """Ask the model who said each line. Returns {sequence_index: role}; empty on failure."""
    subset = segments[:MAX_ATTRIBUTION_SEGMENTS]
    numbered = "\n".join(f"{s['sequence_index']}. {s.get('text', '')}" for s in subset)
    system = (
        "You label who is speaking in a business call transcript that has no speaker information. "
        "Use short role names such as 'Sales Representative', 'Customer', 'Support Agent', 'Manager'. "
        "Base each label only on the content and the flow of the dialogue; consecutive lines may belong "
        "to the same person. Use at most 4 distinct roles. "
        'Return JSON: {"segments": [{"i": <line number>, "speaker": <role>}]} covering every line.'
    )
    result = await _safe_call_agent(llm, system, numbered, "speaker_attribution")
    roles: dict[int, str] = {}
    for item in result.get("segments", []) if isinstance(result.get("segments"), list) else []:
        try:
            idx, speaker = int(item["i"]), str(item["speaker"]).strip()
        except (KeyError, TypeError, ValueError):
            continue
        if speaker:
            roles[idx] = speaker[:50]
    if len({*roles.values()}) > 4:
        logger.warning("Speaker attribution returned too many roles; keeping pause-based labels")
        return {}
    return roles


async def node_clean_transcript(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 1 — Clean raw transcript segments."""
    logger.info("Running transcript cleaning agent")
    segments = state.get("raw_segments", [])

    # Label speakers with human-readable names
    speaker_labels = {}
    speaker_counter = 1
    for seg in segments:
        raw_speaker = seg.get("speaker", "SPEAKER_00")
        if raw_speaker not in speaker_labels:
            speaker_labels[raw_speaker] = f"Speaker {speaker_counter}"
            speaker_counter += 1

    # Apply labels
    labeled_segments = []
    for i, seg in enumerate(segments):
        labeled = dict(seg)
        labeled["speaker_label"] = speaker_labels.get(seg.get("speaker", ""), "Speaker 1")
        labeled["sequence_index"] = i
        labeled_segments.append(labeled)

    # Hosted STT can't tell voices apart, so let the model attribute lines by what is said
    if llm.provider_name != "mock" and labeled_segments:
        roles = await _attribute_speaker_roles(llm, labeled_segments)
        for seg in labeled_segments:
            if seg["sequence_index"] in roles:
                seg["speaker_label"] = roles[seg["sequence_index"]]

    return {
        "raw_segments": labeled_segments,
        "speaker_map": speaker_labels,
        "current_step": "transcript_cleaned",
        "steps_completed": state.get("steps_completed", []) + ["clean_transcript"],
    }


# ---------------------------------------------------------------------------
# Node: Classify conversation
# ---------------------------------------------------------------------------

async def node_classify_conversation(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 2 — Classify conversation type and purpose."""
    logger.info("Running classification agent")
    transcript = _build_transcript_context(state, max_chars=3000)

    system = (
        "You are a conversation classification AI agent. "
        "Analyze the transcript and classify the conversation. "
        "Return a JSON object with these fields: "
        "conversation_type (one of: sales, customer_support, product_demo, follow_up, internal_meeting, "
        "client_meeting, complaint, general_business, other), "
        "primary_purpose (string), business_context (string), confidence (0-1 float)."
    )
    user = f"Classify this conversation:\n\n{transcript}"

    result = await _safe_call_agent(llm, system, user, "classification")

    return {
        "conversation_type": result.get("conversation_type", "general_business"),
        "primary_purpose": result.get("primary_purpose", ""),
        "business_context": result.get("business_context", ""),
        "classification_confidence": float(result.get("confidence", 0.7)),
        "current_step": "classified",
        "steps_completed": state.get("steps_completed", []) + ["classify"],
    }


# ---------------------------------------------------------------------------
# Node: Generate summary
# ---------------------------------------------------------------------------

async def node_summarize(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 3 — Generate executive summary, detailed summary, key topics."""
    logger.info("Running summarization agent")
    transcript = _build_transcript_context(state)
    conv_type = state.get("conversation_type", "general_business")

    system = (
        "You are a professional business conversation summarization AI. "
        "Generate accurate, grounded summaries based strictly on the transcript. "
        "Never invent information not present in the transcript. "
        "Return JSON with: executive_summary (2-3 sentences), "
        "detailed_summary (comprehensive), key_topics (list of strings), "
        "decisions (list of strings), important_moments (list of {timestamp: float, description: string}), "
        "open_questions (list), next_steps (list)."
    )
    user = f"Conversation type: {conv_type}\n\nTranscript:\n{transcript}"

    result = await _safe_call_agent(llm, system, user, "summarization")

    return {
        "executive_summary": result.get("executive_summary", ""),
        "detailed_summary": result.get("detailed_summary", ""),
        "key_topics": result.get("key_topics", []),
        "decisions": result.get("decisions", []),
        "important_moments": result.get("important_moments", []),
        "open_questions": result.get("open_questions", []),
        "next_steps": result.get("next_steps", []),
        "current_step": "summarized",
        "steps_completed": state.get("steps_completed", []) + ["summarize"],
    }


# ---------------------------------------------------------------------------
# Node: Extract action items
# ---------------------------------------------------------------------------

async def node_extract_action_items(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 4 — Extract all actionable tasks from the conversation."""
    logger.info("Running action item extraction agent")
    transcript = _build_transcript_context(state)

    system = (
        "You are an action item extraction AI. "
        "Extract every actionable task mentioned in the conversation. "
        "Return JSON: {action_items: [{description, owner, owner_speaker, due_date, "
        "priority (low|medium|high|urgent), related_topic, timestamp}]} "
        "If owner or due date is unknown, set to null — do not guess."
    )
    user = f"Extract action items from this transcript:\n\n{transcript}"

    result = await _safe_call_agent(llm, system, user, "action_items")

    return {
        "action_items": result.get("action_items", []),
        "current_step": "action_items_extracted",
        "steps_completed": state.get("steps_completed", []) + ["action_items"],
    }


# ---------------------------------------------------------------------------
# Node: Sentiment analysis
# ---------------------------------------------------------------------------

async def node_analyze_sentiment(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 5 — Analyze sentiment throughout the conversation."""
    logger.info("Running sentiment analysis agent")
    transcript = _build_transcript_context(state)

    system = (
        "You are a sentiment analysis AI. Analyze the emotional tone of the conversation. "
        "Important: Do not claim emotion detection is perfectly accurate. "
        "Return JSON: {overall_sentiment (positive|negative|neutral|mixed), "
        "overall_score (-1.0 to 1.0), customer_sentiment, agent_sentiment, "
        "sentiment_trend (string describing progression), "
        "timeline [{timestamp, speaker, sentiment, score}], "
        "positive_moments [{timestamp, description}], "
        "negative_moments [{timestamp, description}], "
        "frustration_detected (bool), satisfaction_detected (bool)}"
    )
    user = f"Analyze sentiment in this transcript:\n\n{transcript}"

    result = await _safe_call_agent(llm, system, user, "sentiment")

    return {
        "overall_sentiment": result.get("overall_sentiment", "neutral"),
        "overall_sentiment_score": float(result.get("overall_score", 0.0)),
        "customer_sentiment": result.get("customer_sentiment", "neutral"),
        "agent_sentiment": result.get("agent_sentiment", "neutral"),
        "sentiment_trend": result.get("sentiment_trend", ""),
        "sentiment_timeline": result.get("timeline", []),
        "positive_moments": result.get("positive_moments", []),
        "negative_moments": result.get("negative_moments", []),
        "frustration_detected": bool(result.get("frustration_detected", False)),
        "satisfaction_detected": bool(result.get("satisfaction_detected", False)),
        "current_step": "sentiment_analyzed",
        "steps_completed": state.get("steps_completed", []) + ["sentiment"],
    }


# ---------------------------------------------------------------------------
# Node: Customer intent
# ---------------------------------------------------------------------------

async def node_analyze_intent(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 6 — Determine customer intent."""
    logger.info("Running intent analysis agent")
    transcript = _build_transcript_context(state)

    system = (
        "You are a customer intent analysis AI. Determine what the customer wants. "
        "Possible intents: product_inquiry, pricing_inquiry, demo_request, purchase_intent, "
        "support_request, complaint, cancellation, upgrade, integration_request, feature_request, "
        "information_request, other. "
        "Return JSON: {primary_intent, secondary_intents (list), confidence (0-1), "
        "evidence [{text, timestamp}]}"
    )
    user = f"Analyze customer intent:\n\n{transcript}"

    result = await _safe_call_agent(llm, system, user, "intent")

    return {
        "primary_intent": result.get("primary_intent", "information_request"),
        "secondary_intents": result.get("secondary_intents", []),
        "intent_confidence": float(result.get("confidence", 0.7)),
        "intent_evidence": result.get("evidence", []),
        "current_step": "intent_analyzed",
        "steps_completed": state.get("steps_completed", []) + ["intent"],
    }


# ---------------------------------------------------------------------------
# Node: Pain points
# ---------------------------------------------------------------------------

async def node_extract_pain_points(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 7 — Extract customer pain points and needs."""
    logger.info("Running pain point extraction agent")
    transcript = _build_transcript_context(state)

    system = (
        "You are a pain point analysis AI. Extract customer problems and needs. "
        "Return JSON: {pain_points: [{category (operational|technical|financial|process|other), "
        "description, severity (low|medium|high), desired_outcome, "
        "potential_solution, evidence (exact quote), timestamp}]}"
    )
    user = f"Extract pain points:\n\n{transcript}"

    result = await _safe_call_agent(llm, system, user, "pain_points")

    return {
        "pain_points": result.get("pain_points", []),
        "current_step": "pain_points_extracted",
        "steps_completed": state.get("steps_completed", []) + ["pain_points"],
    }


# ---------------------------------------------------------------------------
# Node: Sales intelligence
# ---------------------------------------------------------------------------

async def node_analyze_sales_intelligence(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 8 — Comprehensive sales intelligence analysis."""
    logger.info("Running sales intelligence agent")
    transcript = _build_transcript_context(state)
    conv_type = state.get("conversation_type", "")

    # Only run full sales analysis for relevant conversation types
    if conv_type not in ("sales", "product_demo", "follow_up", "client_meeting"):
        return {
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
            "steps_completed": state.get("steps_completed", []) + ["sales_intelligence"],
        }

    system = (
        "You are a sales intelligence AI. Analyze the sales dynamics of this conversation. "
        "Return JSON: {lead_score (0-100 int), purchase_intent (low|medium|high), "
        "deal_health (healthy|at_risk|critical), budget_discussed (bool), budget_range (string|null), "
        "decision_maker_present (bool), timeline_discussed (bool), timeline (string|null), "
        "buying_signals [{signal, timestamp, evidence}], "
        "upsell_opportunities (list of strings), cross_sell_opportunities (list), "
        "stage (new|contacted|qualified|demo|proposal|negotiation|won|lost), "
        "closing_probability (0.0-1.0)}"
    )
    user = f"Analyze sales intelligence:\n\n{transcript}"

    result = await _safe_call_agent(llm, system, user, "sales_intelligence")

    return {
        "lead_score": result.get("lead_score"),
        "purchase_intent": result.get("purchase_intent"),
        "deal_health": result.get("deal_health"),
        "budget_discussed": bool(result.get("budget_discussed", False)),
        "budget_range": result.get("budget_range"),
        "decision_maker_present": bool(result.get("decision_maker_present", False)),
        "timeline_discussed": bool(result.get("timeline_discussed", False)),
        "deal_timeline": result.get("timeline"),
        "buying_signals": result.get("buying_signals", []),
        "upsell_opportunities": result.get("upsell_opportunities", []),
        "cross_sell_opportunities": result.get("cross_sell_opportunities", []),
        "pipeline_stage": result.get("stage"),
        "closing_probability": result.get("closing_probability"),
        "current_step": "sales_analyzed",
        "steps_completed": state.get("steps_completed", []) + ["sales_intelligence"],
    }


# ---------------------------------------------------------------------------
# Node: Objections
# ---------------------------------------------------------------------------

async def node_detect_objections(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 9 — Detect and categorize sales objections."""
    logger.info("Running objection detection agent")
    transcript = _build_transcript_context(state)

    system = (
        "You are an objection detection AI. Find all sales objections in the conversation. "
        "Return JSON: {objections: [{category (price|features|security|integration|competitor|"
        "timing|contract|complexity|trust|implementation|support|other), "
        "description, exact_quote, timestamp, severity (low|medium|high), "
        "was_resolved (bool), suggested_response}]}"
    )
    user = f"Detect objections:\n\n{transcript}"

    result = await _safe_call_agent(llm, system, user, "objections")

    return {
        "objections": result.get("objections", []),
        "current_step": "objections_detected",
        "steps_completed": state.get("steps_completed", []) + ["objections"],
    }


# ---------------------------------------------------------------------------
# Node: Entity extraction
# ---------------------------------------------------------------------------

async def node_extract_entities(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 10 — Extract named entities (competitors, products, companies, etc.)."""
    logger.info("Running entity extraction agent")
    transcript = _build_transcript_context(state)

    system = (
        "You are a named entity extraction AI for business conversations. "
        "Extract all notable entities. "
        "Return JSON: {entities: [{type (competitor|product|company|person|technology|location|price|plan|feature), "
        "value, context, timestamp, sentiment (positive|negative|neutral|null), mention_count (int)}]}"
    )
    user = f"Extract entities:\n\n{transcript}"

    result = await _safe_call_agent(llm, system, user, "entities")

    return {
        "entities": result.get("entities", []),
        "current_step": "entities_extracted",
        "steps_completed": state.get("steps_completed", []) + ["entities"],
    }


# ---------------------------------------------------------------------------
# Node: Meeting minutes
# ---------------------------------------------------------------------------

async def node_generate_meeting_minutes(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 11 — Generate professional meeting minutes."""
    logger.info("Running meeting minutes agent")
    transcript = _build_transcript_context(state)

    system = (
        "You are a professional meeting minutes AI. Generate formal meeting minutes. "
        "Return JSON: {objective, participants_summary, "
        "discussion_points (list), decisions (list), "
        "action_items_summary (list of strings), open_questions (list), "
        "risks (list), next_steps (list), next_meeting (string|null)}"
    )
    user = (
        f"Conversation type: {state.get('conversation_type', '')}\n"
        f"Summary: {state.get('executive_summary', '')}\n\n"
        f"Transcript:\n{transcript}"
    )

    result = await _safe_call_agent(llm, system, user, "meeting_minutes")

    # Build formatted markdown
    minutes_md = _format_minutes_markdown(result)
    result["formatted_markdown"] = minutes_md

    return {
        "meeting_minutes": result,
        "current_step": "minutes_generated",
        "steps_completed": state.get("steps_completed", []) + ["meeting_minutes"],
    }


def _format_minutes_markdown(minutes: dict) -> str:
    """Convert meeting minutes dict to professional markdown."""
    lines = [
        "# Meeting Minutes\n",
        f"## Objective\n{minutes.get('objective', 'N/A')}\n",
        f"## Participants\n{minutes.get('participants_summary', 'N/A')}\n",
        "## Discussion Points",
    ]
    for point in minutes.get("discussion_points", []):
        lines.append(f"- {point}")
    lines.extend([
        "\n## Decisions",
    ])
    for d in minutes.get("decisions", []):
        lines.append(f"- {d}")
    lines.extend(["\n## Action Items"])
    for item in minutes.get("action_items_summary", []):
        lines.append(f"- [ ] {item}")
    lines.extend(["\n## Open Questions"])
    for q in minutes.get("open_questions", []):
        lines.append(f"- {q}")
    lines.extend(["\n## Risks"])
    for r in minutes.get("risks", []):
        lines.append(f"- {r}")
    lines.extend(["\n## Next Steps"])
    for s in minutes.get("next_steps", []):
        lines.append(f"- {s}")
    if minutes.get("next_meeting"):
        lines.append(f"\n## Next Meeting\n{minutes['next_meeting']}")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Node: Recommendations
# ---------------------------------------------------------------------------

async def node_generate_recommendations(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 14 — Generate actionable next-step recommendations."""
    logger.info("Running recommendation agent")

    summary = state.get("executive_summary", "")
    intent = state.get("primary_intent", "")
    lead_score = state.get("lead_score", "N/A")
    deal_health = state.get("deal_health", "N/A")
    objections = state.get("objections", [])

    system = (
        "You are a sales recommendation AI. Based on conversation intelligence, "
        "recommend specific next actions. Every recommendation must have clear reasoning. "
        "Return JSON: {recommendations: [{category, action, reasoning, "
        "priority (high|medium|low), urgency (today|this_week|this_month|before_demo|other), "
        "evidence (list of supporting quotes/signals)}]}"
    )
    user = (
        f"Conversation summary: {summary}\n"
        f"Customer intent: {intent}\n"
        f"Lead score: {lead_score}\n"
        f"Deal health: {deal_health}\n"
        f"Objections count: {len(objections)}\n"
    )

    result = await _safe_call_agent(llm, system, user, "recommendations")

    return {
        "recommendations": result.get("recommendations", []),
        "current_step": "recommendations_generated",
        "steps_completed": state.get("steps_completed", []) + ["recommendations"],
    }


# ---------------------------------------------------------------------------
# Node: CRM update proposals
# ---------------------------------------------------------------------------

async def node_propose_crm_updates(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 13 — Propose CRM field updates (requires human approval before execution)."""
    logger.info("Running CRM update agent")

    system = (
        "You are a CRM update AI. Based on conversation intelligence, propose CRM field updates. "
        "IMPORTANT: These are PROPOSALS only — a human must approve before any CRM write. "
        "Return JSON: {crm_entity_type (lead|contact|opportunity|deal), "
        "proposed_changes: {field: {from, to}}, reasoning}"
    )
    user = (
        f"Lead score: {state.get('lead_score')}\n"
        f"Purchase intent: {state.get('purchase_intent')}\n"
        f"Deal health: {state.get('deal_health')}\n"
        f"Stage: {state.get('pipeline_stage')}\n"
        f"Summary: {state.get('executive_summary', '')[:500]}\n"
    )

    result = await _safe_call_agent(llm, system, user, "crm_update")

    return {
        "crm_proposed_changes": result,
        "current_step": "crm_proposals_generated",
        "steps_completed": state.get("steps_completed", []) + ["crm_update"],
    }


# ---------------------------------------------------------------------------
# Node: Agent performance scoring
# ---------------------------------------------------------------------------

async def node_score_agent_performance(state: ConversationState, llm: LLMProvider) -> dict:
    """Agent 15 — Evaluate agent performance (labeled as AI assessment)."""
    logger.info("Running agent QA scoring node")
    transcript = _build_transcript_context(state)

    system = (
        "You are a sales/support agent quality assessment AI. "
        "IMPORTANT: Always clearly label outputs as AI-generated assessments, not objective facts. "
        "Evaluate the agent's performance. "
        "Return JSON: {overall_score (0-100), greeting_score, professionalism_score, "
        "empathy_score, listening_score, question_quality_score, product_knowledge_score, "
        "objection_handling_score, closing_score, talk_ratio (agent_words/total_words as float), "
        "interruption_count, filler_word_count, strengths (list), weaknesses (list), "
        "improvement_suggestions (list), coaching_notes (string), "
        "disclaimer (must include: This is an AI-generated assessment)}"
    )
    user = f"Evaluate agent performance:\n\n{transcript}"

    result = await _safe_call_agent(llm, system, user, "agent_score")

    return {
        "agent_score": result,
        "current_step": "agent_scored",
        "steps_completed": state.get("steps_completed", []) + ["agent_score"],
        "status": "completed",
    }
