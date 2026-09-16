"""
LangGraph Conversation Processing Pipeline State.

ConversationState is the shared state object passed between all agents in the graph.
Every agent reads from it and writes back its results.

Using TypedDict ensures type safety while being compatible with LangGraph.
"""

from typing import Any, TypedDict


class TranscriptSegmentData(TypedDict):
    speaker: str          # "SPEAKER_00"
    speaker_label: str    # "Speaker 1" (human readable)
    start: float
    end: float
    text: str
    confidence: float | None
    sequence_index: int


class ConversationState(TypedDict):
    """
    Shared state flowing through the LangGraph pipeline.

    Fields are populated incrementally as agents process the conversation.
    Errors are accumulated (not raised) to allow partial results.
    """

    # ---- Input ----
    conversation_id: str
    organization_id: str
    audio_file_path: str | None
    uploaded_file_name: str | None

    # ---- Transcription ----
    raw_segments: list[TranscriptSegmentData]
    full_transcript_text: str
    language: str
    duration_seconds: float
    speaker_map: dict[str, str]   # {"SPEAKER_00": "Speaker 1", ...}

    # ---- Classification ----
    conversation_type: str        # sales | support | meeting | demo | follow_up | internal | other
    primary_purpose: str
    business_context: str
    classification_confidence: float

    # ---- Summary ----
    executive_summary: str
    detailed_summary: str
    key_topics: list[str]
    decisions: list[dict]
    important_moments: list[dict]  # [{timestamp, description}]
    open_questions: list[str]
    next_steps: list[str]

    # ---- Action Items ----
    action_items: list[dict]

    # ---- Sentiment ----
    overall_sentiment: str
    overall_sentiment_score: float
    customer_sentiment: str
    agent_sentiment: str
    sentiment_trend: str
    sentiment_timeline: list[dict]
    positive_moments: list[dict]
    negative_moments: list[dict]
    frustration_detected: bool
    satisfaction_detected: bool

    # ---- Intent ----
    primary_intent: str
    secondary_intents: list[str]
    intent_confidence: float
    intent_evidence: list[dict]

    # ---- Pain Points ----
    pain_points: list[dict]

    # ---- Sales Intelligence ----
    lead_score: int | None                    # 0-100
    purchase_intent: str | None               # low | medium | high
    deal_health: str | None                   # healthy | at_risk | critical
    budget_discussed: bool
    budget_range: str | None
    decision_maker_present: bool
    timeline_discussed: bool
    deal_timeline: str | None
    buying_signals: list[dict]
    upsell_opportunities: list[str]
    cross_sell_opportunities: list[str]
    pipeline_stage: str | None
    closing_probability: float | None

    # ---- Objections ----
    objections: list[dict]

    # ---- Entities ----
    entities: list[dict]   # competitors, products, companies, people, etc.

    # ---- Meeting Minutes ----
    meeting_minutes: dict | None

    # ---- Recommendations ----
    recommendations: list[dict]

    # ---- CRM Update ----
    crm_proposed_changes: dict | None

    # ---- Agent Score ----
    agent_score: dict | None

    # ---- Generated Email ----
    generated_email: dict | None

    # ---- Processing ----
    current_step: str
    steps_completed: list[str]
    errors: list[str]   # Accumulated errors (don't stop pipeline)
    status: str         # processing | completed | failed
