"""
SQLAlchemy ORM models for TalkWiseAI.

All models use UUIDs as primary keys for global uniqueness.
Every organization-scoped model includes organization_id for multi-tenancy.
"""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.session import Base


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.utcnow()


# ---------------------------------------------------------------------------
# Organizations
# ---------------------------------------------------------------------------

class Organization(Base):
    __tablename__ = "organizations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    slug: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    plan: Mapped[str] = mapped_column(String(50), default="free")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    settings: Mapped[dict | None] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    users: Mapped[list["User"]] = relationship("User", back_populates="organization")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="organization")
    integrations: Mapped[list["Integration"]] = relationship("Integration", back_populates="organization")


# ---------------------------------------------------------------------------
# Users & Auth
# ---------------------------------------------------------------------------

class Role(Base):
    __tablename__ = "roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)  # admin | manager | agent
    description: Mapped[str | None] = mapped_column(Text)
    permissions: Mapped[dict | None] = mapped_column(JSON, default=dict)

    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="role")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512))
    preferences: Mapped[dict] = mapped_column(JSON, default=dict)
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="users")
    user_roles: Mapped[list["UserRole"]] = relationship("UserRole", back_populates="user", cascade="all, delete-orphan")
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="created_by_user")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="user")

    __table_args__ = (Index("ix_users_email", "email"), Index("ix_users_org", "organization_id"))


class UserRole(Base):
    __tablename__ = "user_roles"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    role_id: Mapped[str] = mapped_column(String(36), ForeignKey("roles.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped["User"] = relationship("User", back_populates="user_roles")
    role: Mapped["Role"] = relationship("Role", back_populates="user_roles")

    __table_args__ = (Index("ix_user_roles_user", "user_id"),)


# ---------------------------------------------------------------------------
# Conversations
# ---------------------------------------------------------------------------

class Conversation(Base):
    """Central entity — every insight hangs off a Conversation."""
    __tablename__ = "conversations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    conversation_type: Mapped[str] = mapped_column(
        String(50), default="unknown"
    )  # sales | support | meeting | demo | follow_up | internal | other
    status: Mapped[str] = mapped_column(
        String(50), default="uploaded"
    )  # uploaded | queued | processing | transcribing | analyzing | completed | failed
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    language: Mapped[str] = mapped_column(String(10), default="en")
    file_path: Mapped[str | None] = mapped_column(String(1024))
    file_name: Mapped[str | None] = mapped_column(String(512))
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    file_type: Mapped[str | None] = mapped_column(String(50))  # audio | video
    error_message: Mapped[str | None] = mapped_column(Text)
    extra_metadata: Mapped[dict] = mapped_column("extra_metadata", JSON, default=dict)
    occurred_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="conversations")
    created_by_user: Mapped["User"] = relationship("User", back_populates="conversations")
    participants: Mapped[list["Participant"]] = relationship("Participant", back_populates="conversation", cascade="all, delete-orphan")
    speakers: Mapped[list["Speaker"]] = relationship("Speaker", back_populates="conversation", cascade="all, delete-orphan")
    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship("TranscriptSegment", back_populates="conversation", cascade="all, delete-orphan")
    processing_jobs: Mapped[list["ProcessingJob"]] = relationship("ProcessingJob", back_populates="conversation", cascade="all, delete-orphan")
    summary: Mapped["Summary | None"] = relationship("Summary", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    sentiment: Mapped["SentimentResult | None"] = relationship("SentimentResult", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    intent_result: Mapped["IntentResult | None"] = relationship("IntentResult", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    sales_insight: Mapped["SalesInsight | None"] = relationship("SalesInsight", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    action_items: Mapped[list["ActionItem"]] = relationship("ActionItem", back_populates="conversation", cascade="all, delete-orphan")
    objections: Mapped[list["Objection"]] = relationship("Objection", back_populates="conversation", cascade="all, delete-orphan")
    entities: Mapped[list["Entity"]] = relationship("Entity", back_populates="conversation", cascade="all, delete-orphan")
    pain_points: Mapped[list["PainPoint"]] = relationship("PainPoint", back_populates="conversation", cascade="all, delete-orphan")
    meeting_minutes: Mapped["MeetingMinutes | None"] = relationship("MeetingMinutes", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    recommendations: Mapped[list["Recommendation"]] = relationship("Recommendation", back_populates="conversation", cascade="all, delete-orphan")
    agent_score: Mapped["AgentScore | None"] = relationship("AgentScore", back_populates="conversation", uselist=False, cascade="all, delete-orphan")
    notifications: Mapped[list["Notification"]] = relationship("Notification", back_populates="conversation", cascade="all, delete-orphan")

    __table_args__ = (
        Index("ix_conversations_org", "organization_id"),
        Index("ix_conversations_status", "status"),
        Index("ix_conversations_type", "conversation_type"),
        Index("ix_conversations_created", "created_at"),
    )


class Participant(Base):
    __tablename__ = "participants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str | None] = mapped_column(String(255))
    role: Mapped[str | None] = mapped_column(String(100))  # sales_rep | customer | manager | etc.
    is_agent: Mapped[bool] = mapped_column(Boolean, default=False)
    crm_contact_id: Mapped[str | None] = mapped_column(String(255))

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="participants")


class Speaker(Base):
    """Speaker identified via diarization — can be renamed by users."""
    __tablename__ = "speakers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    speaker_label: Mapped[str] = mapped_column(String(50), nullable=False)   # "Speaker 1"
    display_name: Mapped[str | None] = mapped_column(String(255))             # User-set: "John (Sales Rep)"
    role: Mapped[str | None] = mapped_column(String(100))
    talk_time_seconds: Mapped[float | None] = mapped_column(Float)
    word_count: Mapped[int | None] = mapped_column(Integer)
    crm_user_id: Mapped[str | None] = mapped_column(String(255))

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="speakers")
    transcript_segments: Mapped[list["TranscriptSegment"]] = relationship("TranscriptSegment", back_populates="speaker")


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    speaker_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("speakers.id"))
    speaker_label: Mapped[str | None] = mapped_column(String(50))
    start_time: Mapped[float] = mapped_column(Float, nullable=False)          # seconds from start
    end_time: Mapped[float] = mapped_column(Float, nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    confidence: Mapped[float | None] = mapped_column(Float)
    sequence_index: Mapped[int] = mapped_column(Integer, default=0)
    is_important: Mapped[bool] = mapped_column(Boolean, default=False)
    importance_reason: Mapped[str | None] = mapped_column(String(255))

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="transcript_segments")
    speaker: Mapped["Speaker | None"] = relationship("Speaker", back_populates="transcript_segments")

    __table_args__ = (
        Index("ix_segments_conversation", "conversation_id"),
        Index("ix_segments_start_time", "start_time"),
    )


# ---------------------------------------------------------------------------
# Processing Jobs
# ---------------------------------------------------------------------------

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    celery_task_id: Mapped[str | None] = mapped_column(String(255))
    job_type: Mapped[str] = mapped_column(String(50), default="full_pipeline")
    status: Mapped[str] = mapped_column(String(50), default="queued")
    progress: Mapped[int] = mapped_column(Integer, default=0)  # 0-100
    current_step: Mapped[str | None] = mapped_column(String(100))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="processing_jobs")


# ---------------------------------------------------------------------------
# AI Intelligence Results
# ---------------------------------------------------------------------------

class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), unique=True, nullable=False)
    executive_summary: Mapped[str] = mapped_column(Text)
    detailed_summary: Mapped[str] = mapped_column(Text)
    key_topics: Mapped[list] = mapped_column(JSON, default=list)
    decisions: Mapped[list] = mapped_column(JSON, default=list)
    important_moments: Mapped[list] = mapped_column(JSON, default=list)  # [{timestamp, description}]
    open_questions: Mapped[list] = mapped_column(JSON, default=list)
    next_steps: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="summary")


class SentimentResult(Base):
    __tablename__ = "sentiments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), unique=True, nullable=False)
    overall_sentiment: Mapped[str] = mapped_column(String(20))  # positive | negative | neutral | mixed
    overall_score: Mapped[float | None] = mapped_column(Float)   # -1.0 to 1.0
    customer_sentiment: Mapped[str | None] = mapped_column(String(20))
    agent_sentiment: Mapped[str | None] = mapped_column(String(20))
    sentiment_trend: Mapped[str | None] = mapped_column(String(100))  # "Neutral → Interested → Positive"
    timeline: Mapped[list] = mapped_column(JSON, default=list)          # [{timestamp, speaker, sentiment, score}]
    positive_moments: Mapped[list] = mapped_column(JSON, default=list)
    negative_moments: Mapped[list] = mapped_column(JSON, default=list)
    frustration_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    satisfaction_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="sentiment")


class IntentResult(Base):
    __tablename__ = "intents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), unique=True, nullable=False)
    primary_intent: Mapped[str] = mapped_column(String(100))
    secondary_intents: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float | None] = mapped_column(Float)
    evidence: Mapped[list] = mapped_column(JSON, default=list)  # [{text, timestamp}]
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="intent_result")


class SalesInsight(Base):
    __tablename__ = "sales_insights"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), unique=True, nullable=False)
    lead_score: Mapped[int | None] = mapped_column(Integer)           # 0-100
    purchase_intent: Mapped[str | None] = mapped_column(String(20))   # low | medium | high
    deal_health: Mapped[str | None] = mapped_column(String(20))       # healthy | at_risk | critical
    budget_discussed: Mapped[bool] = mapped_column(Boolean, default=False)
    budget_range: Mapped[str | None] = mapped_column(String(255))
    decision_maker_present: Mapped[bool] = mapped_column(Boolean, default=False)
    timeline_discussed: Mapped[bool] = mapped_column(Boolean, default=False)
    timeline: Mapped[str | None] = mapped_column(String(255))
    buying_signals: Mapped[list] = mapped_column(JSON, default=list)  # [{signal, timestamp, evidence}]
    upsell_opportunities: Mapped[list] = mapped_column(JSON, default=list)
    cross_sell_opportunities: Mapped[list] = mapped_column(JSON, default=list)
    stage: Mapped[str | None] = mapped_column(String(50))  # new | contacted | qualified | demo | proposal | negotiation | won | lost
    closing_probability: Mapped[float | None] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="sales_insight")


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner: Mapped[str | None] = mapped_column(String(255))
    owner_speaker_label: Mapped[str | None] = mapped_column(String(50))
    due_date: Mapped[str | None] = mapped_column(String(100))           # Raw text from transcript
    due_date_parsed: Mapped[datetime | None] = mapped_column(DateTime)
    priority: Mapped[str] = mapped_column(String(20), default="medium")  # low | medium | high | urgent
    status: Mapped[str] = mapped_column(String(20), default="pending")   # pending | in_progress | completed | overdue
    source_timestamp: Mapped[float | None] = mapped_column(Float)        # seconds into conversation
    related_topic: Mapped[str | None] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="action_items")

    __table_args__ = (Index("ix_action_items_org", "organization_id"),)


class Objection(Base):
    __tablename__ = "objections"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(100))  # price | features | security | competitor | timing | etc.
    description: Mapped[str] = mapped_column(Text)
    exact_quote: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[float | None] = mapped_column(Float)
    severity: Mapped[str] = mapped_column(String(20), default="medium")   # low | medium | high
    was_resolved: Mapped[bool] = mapped_column(Boolean, default=False)
    suggested_response: Mapped[str | None] = mapped_column(Text)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="objections")


class Entity(Base):
    __tablename__ = "entities"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(50))  # competitor | product | company | person | location | technology | price | plan
    value: Mapped[str] = mapped_column(String(500), nullable=False)
    context: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[float | None] = mapped_column(Float)
    sentiment: Mapped[str | None] = mapped_column(String(20))
    mention_count: Mapped[int] = mapped_column(Integer, default=1)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="entities")


class PainPoint(Base):
    __tablename__ = "pain_points"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(100))  # operational | technical | financial | process | etc.
    description: Mapped[str] = mapped_column(Text, nullable=False)
    severity: Mapped[str] = mapped_column(String(20), default="medium")
    desired_outcome: Mapped[str | None] = mapped_column(Text)
    potential_solution: Mapped[str | None] = mapped_column(Text)
    evidence: Mapped[str | None] = mapped_column(Text)
    timestamp: Mapped[float | None] = mapped_column(Float)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="pain_points")


class MeetingMinutes(Base):
    __tablename__ = "meeting_minutes"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), unique=True, nullable=False)
    objective: Mapped[str | None] = mapped_column(Text)
    participants_summary: Mapped[str | None] = mapped_column(Text)
    discussion_points: Mapped[list] = mapped_column(JSON, default=list)
    decisions: Mapped[list] = mapped_column(JSON, default=list)
    action_items_summary: Mapped[list] = mapped_column(JSON, default=list)
    open_questions: Mapped[list] = mapped_column(JSON, default=list)
    risks: Mapped[list] = mapped_column(JSON, default=list)
    next_steps: Mapped[list] = mapped_column(JSON, default=list)
    next_meeting: Mapped[str | None] = mapped_column(String(255))
    formatted_markdown: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="meeting_minutes")


class Recommendation(Base):
    __tablename__ = "recommendations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    category: Mapped[str] = mapped_column(String(100))  # follow_up | demo | proposal | escalate | etc.
    action: Mapped[str] = mapped_column(Text, nullable=False)
    reasoning: Mapped[str | None] = mapped_column(Text)
    priority: Mapped[str] = mapped_column(String(20), default="medium")
    urgency: Mapped[str] = mapped_column(String(20), default="normal")
    evidence: Mapped[list] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="recommendations")


class AgentScore(Base):
    __tablename__ = "agent_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), unique=True, nullable=False)
    overall_score: Mapped[int | None] = mapped_column(Integer)  # 0-100
    greeting_score: Mapped[int | None] = mapped_column(Integer)
    professionalism_score: Mapped[int | None] = mapped_column(Integer)
    empathy_score: Mapped[int | None] = mapped_column(Integer)
    listening_score: Mapped[int | None] = mapped_column(Integer)
    question_quality_score: Mapped[int | None] = mapped_column(Integer)
    product_knowledge_score: Mapped[int | None] = mapped_column(Integer)
    objection_handling_score: Mapped[int | None] = mapped_column(Integer)
    closing_score: Mapped[int | None] = mapped_column(Integer)
    talk_ratio: Mapped[float | None] = mapped_column(Float)  # agent talk / total talk
    interruption_count: Mapped[int | None] = mapped_column(Integer)
    filler_word_count: Mapped[int | None] = mapped_column(Integer)
    strengths: Mapped[list | None] = mapped_column(JSON, default=list)
    weaknesses: Mapped[list | None] = mapped_column(JSON, default=list)
    improvement_suggestions: Mapped[list | None] = mapped_column(JSON, default=list)
    coaching_notes: Mapped[str | None] = mapped_column(Text)
    disclaimer: Mapped[str] = mapped_column(Text, default="This is an AI-generated assessment and should be used as one input among many.")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    conversation: Mapped["Conversation"] = relationship("Conversation", back_populates="agent_score")


# ---------------------------------------------------------------------------
# Knowledge Base
# ---------------------------------------------------------------------------

class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    uploaded_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(500), nullable=False)
    file_name: Mapped[str] = mapped_column(String(512), nullable=False)
    file_path: Mapped[str] = mapped_column(String(1024), nullable=False)
    file_type: Mapped[str] = mapped_column(String(50))  # pdf | docx | txt | md
    file_size_bytes: Mapped[int | None] = mapped_column(Integer)
    status: Mapped[str] = mapped_column(String(50), default="processing")  # processing | indexed | failed
    chunk_count: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    chunks: Mapped[list["KnowledgeChunk"]] = relationship("KnowledgeChunk", back_populates="document", cascade="all, delete-orphan")

    __table_args__ = (Index("ix_knowledge_docs_org", "organization_id"),)


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    document_id: Mapped[str] = mapped_column(String(36), ForeignKey("knowledge_documents.id"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    vector_id: Mapped[str | None] = mapped_column(String(255))  # ID in ChromaDB
    extra_metadata: Mapped[dict | None] = mapped_column("extra_metadata", JSON, default=dict)

    document: Mapped["KnowledgeDocument"] = relationship("KnowledgeDocument", back_populates="chunks")


# ---------------------------------------------------------------------------
# Integrations & CRM
# ---------------------------------------------------------------------------

class Integration(Base):
    __tablename__ = "integrations"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), ForeignKey("organizations.id"), nullable=False)
    integration_type: Mapped[str] = mapped_column(String(50))  # crm | calendar | email | talkwisely
    provider: Mapped[str] = mapped_column(String(50))           # mock | hubspot | salesforce | google | etc.
    is_enabled: Mapped[bool] = mapped_column(Boolean, default=False)
    is_connected: Mapped[bool] = mapped_column(Boolean, default=False)
    config: Mapped[dict] = mapped_column(JSON, default=dict)    # Non-secret config (no API keys)
    last_synced_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    organization: Mapped["Organization"] = relationship("Organization", back_populates="integrations")


class CRMRecord(Base):
    """Tracks proposed and approved CRM updates from AI analysis."""
    __tablename__ = "crm_records"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    conversation_id: Mapped[str] = mapped_column(String(36), ForeignKey("conversations.id"), nullable=False)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    crm_entity_type: Mapped[str] = mapped_column(String(50))  # lead | contact | opportunity | deal
    crm_entity_id: Mapped[str | None] = mapped_column(String(255))
    proposed_changes: Mapped[dict] = mapped_column(JSON, default=dict)
    status: Mapped[str] = mapped_column(String(20), default="pending")  # pending | approved | rejected | applied
    approved_by: Mapped[str | None] = mapped_column(String(36))
    applied_at: Mapped[datetime | None] = mapped_column(DateTime)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


# ---------------------------------------------------------------------------
# Notifications
# ---------------------------------------------------------------------------

class Notification(Base):
    __tablename__ = "notifications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    conversation_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("conversations.id"))
    type: Mapped[str] = mapped_column(String(50))  # processing_complete | failed | follow_up | high_intent | etc.
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    user: Mapped["User"] = relationship("User", back_populates="notifications")
    conversation: Mapped["Conversation | None"] = relationship("Conversation", back_populates="notifications")

    __table_args__ = (Index("ix_notifications_user", "user_id"),)


# ---------------------------------------------------------------------------
# Reports & Audit
# ---------------------------------------------------------------------------

class Report(Base):
    __tablename__ = "reports"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36), nullable=False)
    created_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"))
    report_type: Mapped[str] = mapped_column(String(50))   # daily | weekly | monthly | sales | sentiment | agent | objection | executive
    title: Mapped[str] = mapped_column(String(500))
    date_from: Mapped[datetime | None] = mapped_column(DateTime)
    date_to: Mapped[datetime | None] = mapped_column(DateTime)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    file_path: Mapped[str | None] = mapped_column(String(1024))
    status: Mapped[str] = mapped_column(String(20), default="generating")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    organization_id: Mapped[str] = mapped_column(String(36))
    user_id: Mapped[str | None] = mapped_column(String(36))
    action: Mapped[str] = mapped_column(String(100), nullable=False)  # login | upload | delete | crm_approve | etc.
    resource_type: Mapped[str | None] = mapped_column(String(50))
    resource_id: Mapped[str | None] = mapped_column(String(255))
    details: Mapped[dict | None] = mapped_column(JSON, default=dict)
    ip_address: Mapped[str | None] = mapped_column(String(50))
    user_agent: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)

    __table_args__ = (
        Index("ix_audit_org", "organization_id"),
        Index("ix_audit_user", "user_id"),
        Index("ix_audit_action", "action"),
    )
