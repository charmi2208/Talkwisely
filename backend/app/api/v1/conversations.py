"""
Conversations API Routes.

GET    /api/v1/conversations                       — List conversations (paginated, filtered)
POST   /api/v1/conversations/upload                — Upload audio/video file
GET    /api/v1/conversations/{id}                  — Conversation details
DELETE /api/v1/conversations/{id}                  — Delete conversation and its data
GET    /api/v1/conversations/{id}/audio            — Stream the recording
GET    /api/v1/conversations/{id}/transcript       — Transcript segments, speakers, talk time
PATCH  /api/v1/conversations/{id}/speaker-labels   — Rename speakers in the transcript
GET    /api/v1/conversations/{id}/insights         — All AI insights
GET    /api/v1/conversations/{id}/processing-status — Poll pipeline progress
POST   /api/v1/conversations/{id}/reprocess        — Re-run transcription and the AI pipeline

Agents only see conversations they uploaded; admins and managers see the whole
organization (see app/core/access.py).
"""

import os
import shutil
import uuid
from datetime import datetime
from pathlib import Path
from typing import Optional

import aiofiles
from fastapi import APIRouter, BackgroundTasks, Depends, File, Form, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import delete as sa_delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.ai.rag.vector_store import vector_store
from app.core.access import conversation_scope
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.core.logging import get_logger
from app.db.models import (
    ActionItem, AuditLog, Conversation, CRMRecord, MeetingMinutes, Objection, ProcessingJob,
    Recommendation, SalesInsight, SentimentResult, Speaker, Summary, TranscriptSegment, IntentResult
)

router = APIRouter(prefix="/conversations", tags=["Conversations"])
logger = get_logger("conversations.routes")


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class ConversationListItem(BaseModel):
    id: str
    title: str
    conversation_type: str
    status: str
    duration_seconds: int | None
    language: str
    file_name: str | None
    lead_score: int | None = None
    overall_sentiment: str | None = None
    created_at: datetime
    occurred_at: datetime | None

    class Config:
        from_attributes = True


class ConversationListResponse(BaseModel):
    items: list[ConversationListItem]
    total: int
    page: int
    page_size: int
    total_pages: int


class ConversationDetail(BaseModel):
    id: str
    title: str
    conversation_type: str
    status: str
    duration_seconds: int | None
    language: str
    file_name: str | None
    error_message: str | None
    created_at: datetime
    speakers: list[dict] = []

    class Config:
        from_attributes = True


class UploadResponse(BaseModel):
    conversation_id: str
    job_id: str
    title: str
    status: str
    message: str


class TranscriptResponse(BaseModel):
    conversation_id: str
    language: str
    duration_seconds: float | None
    segments: list[dict]
    speakers: list[dict]
    speaker_stats: list[dict] = []


class InsightsResponse(BaseModel):
    conversation_id: str
    summary: dict | None
    sentiment: dict | None
    intent: dict | None
    sales_insight: dict | None
    action_items: list[dict]
    objections: list[dict]
    entities: list[dict]
    pain_points: list[dict]
    recommendations: list[dict]
    meeting_minutes: dict | None
    agent_score: dict | None


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

ALLOWED_EXTENSIONS = set(settings.allowed_audio_extensions + settings.allowed_video_extensions)
MAX_FILE_SIZE = settings.storage_max_upload_size_mb * 1024 * 1024


def _validate_file(filename: str, file_size: int) -> tuple[bool, str]:
    """Return (is_valid, error_message)."""
    ext = Path(filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        return False, f"File type '{ext}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
    if file_size > MAX_FILE_SIZE:
        return False, f"File too large. Maximum size: {settings.storage_max_upload_size_mb} MB"
    return True, ""


async def _save_upload(upload_file: UploadFile, dest_dir: str) -> tuple[str, int]:
    """Save uploaded file to storage, return (file_path, file_size_bytes)."""
    os.makedirs(dest_dir, exist_ok=True)
    safe_name = f"{uuid.uuid4()}{Path(upload_file.filename or 'file').suffix.lower()}"
    dest_path = os.path.join(dest_dir, safe_name)

    size = 0
    async with aiofiles.open(dest_path, "wb") as f:
        while chunk := await upload_file.read(1024 * 1024):  # Read in 1MB chunks
            await f.write(chunk)
            size += len(chunk)

    return dest_path, size


async def _enqueue(db: AsyncSession, background_tasks: BackgroundTasks, conv_id: str, job_id: str, file_path: str) -> None:
    from app.workers.conversation_tasks import enqueue_conversation_processing

    task_id = enqueue_conversation_processing(background_tasks, conv_id, job_id, file_path)
    if task_id:
        job = await db.get(ProcessingJob, job_id)
        if job:
            job.celery_task_id = task_id
            await db.commit()


def _speaker_stats(segments) -> list[dict]:
    """Talk time, turns and word count per transcript speaker label, longest first."""
    stats: dict[str, dict] = {}
    for seg in segments:
        label = seg.speaker_label or "Unknown speaker"
        entry = stats.setdefault(label, {"label": label, "turns": 0, "talk_time_seconds": 0.0, "words": 0})
        entry["turns"] += 1
        entry["talk_time_seconds"] += max(0.0, (seg.end_time or 0) - (seg.start_time or 0))
        entry["words"] += len((seg.text or "").split())
    total = sum(e["talk_time_seconds"] for e in stats.values()) or 1.0
    for entry in stats.values():
        entry["talk_time_seconds"] = round(entry["talk_time_seconds"], 1)
        entry["talk_share"] = round(entry["talk_time_seconds"] / total, 3)
    return sorted(stats.values(), key=lambda e: e["talk_time_seconds"], reverse=True)


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get("", response_model=ConversationListResponse)
async def list_conversations(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    conversation_type: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    search: Optional[str] = Query(None),
    date_from: Optional[str] = Query(None),
    date_to: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List conversations for the current user's organization."""
    from sqlalchemy import and_, or_

    filters = conversation_scope(current_user)

    if conversation_type:
        filters.append(Conversation.conversation_type == conversation_type)
    if status_filter:
        filters.append(Conversation.status == status_filter)
    if search:
        filters.append(Conversation.title.ilike(f"%{search}%"))
    if date_from:
        try:
            filters.append(Conversation.created_at >= datetime.fromisoformat(date_from))
        except ValueError:
            pass
    if date_to:
        try:
            filters.append(Conversation.created_at <= datetime.fromisoformat(date_to))
        except ValueError:
            pass

    # Count total
    count_result = await db.execute(
        select(func.count(Conversation.id)).where(and_(*filters))
    )
    total = count_result.scalar_one()

    # Fetch page
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.sales_insight), selectinload(Conversation.sentiment))
        .where(and_(*filters))
        .order_by(Conversation.created_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
    )
    conversations = result.scalars().all()

    items = []
    for c in conversations:
        lead_score = c.sales_insight.lead_score if c.sales_insight else None
        overall_sentiment = c.sentiment.overall_sentiment if c.sentiment else None
        items.append(ConversationListItem(
            id=c.id,
            title=c.title,
            conversation_type=c.conversation_type,
            status=c.status,
            duration_seconds=c.duration_seconds,
            language=c.language,
            file_name=c.file_name,
            lead_score=lead_score,
            overall_sentiment=overall_sentiment,
            created_at=c.created_at,
            occurred_at=c.occurred_at,
        ))

    total_pages = max(1, -(-total // page_size))  # Ceiling division

    return ConversationListResponse(
        items=items,
        total=total,
        page=page,
        page_size=page_size,
        total_pages=total_pages,
    )


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_conversation(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    title: str = Form(...),
    occurred_at: Optional[str] = Form(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Upload an audio/video file and queue it for AI processing."""
    # Validate file
    file_content = await file.read(1024)  # Read first KB to check size indicator
    await file.seek(0)

    filename = file.filename or "upload"
    is_valid, err = _validate_file(filename, file.size or 0)
    if not is_valid:
        raise HTTPException(status_code=422, detail=err)

    # Save file
    upload_dir = os.path.join(settings.storage_local_path, "uploads", current_user.organization_id)
    file_path, file_size = await _save_upload(file, upload_dir)

    file_type = "audio" if Path(filename).suffix.lower() in settings.allowed_audio_extensions else "video"

    # Create conversation record
    conv_id = str(uuid.uuid4())
    job_id = str(uuid.uuid4())

    conv = Conversation(
        id=conv_id,
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        title=title.strip(),
        status="uploaded",
        file_path=file_path,
        file_name=filename,
        file_size_bytes=file_size,
        file_type=file_type,
        occurred_at=datetime.fromisoformat(occurred_at) if occurred_at else datetime.utcnow(),
    )
    db.add(conv)

    # Create processing job
    job = ProcessingJob(
        id=job_id,
        conversation_id=conv_id,
        job_type="full_pipeline",
        status="queued",
        progress=0,
        current_step="Queued",
    )
    db.add(job)

    # Audit log
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="upload",
        resource_type="conversation",
        resource_id=conv_id,
        details={"filename": filename, "file_size": file_size},
    ))

    await db.commit()

    # Process in the background (in-process or on Celery, per TASK_QUEUE)
    await _enqueue(db, background_tasks, conv_id, job_id, file_path)

    logger.info("Conversation uploaded and queued", conv_id=conv_id, job_id=job_id)

    return UploadResponse(
        conversation_id=conv_id,
        job_id=job_id,
        title=title,
        status="queued",
        message="File uploaded successfully. Processing has started.",
    )


@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(
    conversation_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get conversation details by ID."""
    result = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.speakers))
        .where(
            Conversation.id == conversation_id,
            *conversation_scope(current_user),
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    speakers_data = [
        {
            "id": s.id,
            "speaker_label": s.speaker_label,
            "display_name": s.display_name or s.speaker_label,
            "role": s.role,
            "talk_time_seconds": s.talk_time_seconds,
        }
        for s in conv.speakers
    ]

    return ConversationDetail(
        id=conv.id,
        title=conv.title,
        conversation_type=conv.conversation_type,
        status=conv.status,
        duration_seconds=conv.duration_seconds,
        language=conv.language,
        file_name=conv.file_name,
        error_message=conv.error_message,
        created_at=conv.created_at,
        speakers=speakers_data,
    )


@router.get("/{conversation_id}/audio")
async def get_conversation_audio(
    conversation_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Stream or download the recorded audio file for a conversation."""
    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            *conversation_scope(current_user),
        )
    )
    conv = result.scalar_one_or_none()
    if not conv or not conv.file_path or not os.path.exists(conv.file_path):
        raise HTTPException(status_code=404, detail="Audio file not found")

    ext = Path(conv.file_path).suffix.lower()
    media_type = (
        "audio/mpeg" if ext == ".mp3" else
        "audio/wav" if ext == ".wav" else
        "video/mp4" if ext == ".mp4" else
        "audio/m4a"
    )
    return FileResponse(conv.file_path, media_type=media_type, filename=conv.file_name or "recording")


@router.get("/{conversation_id}/transcript", response_model=TranscriptResponse)
async def get_transcript(
    conversation_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get transcript segments for a conversation."""
    # Verify ownership
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            *conversation_scope(current_user),
        )
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Load segments ordered by sequence
    seg_result = await db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.conversation_id == conversation_id)
        .order_by(TranscriptSegment.sequence_index)
    )
    segments = seg_result.scalars().all()

    # Load speakers
    spk_result = await db.execute(
        select(Speaker).where(Speaker.conversation_id == conversation_id)
    )
    speakers = spk_result.scalars().all()

    return TranscriptResponse(
        conversation_id=conversation_id,
        language=conv.language,
        duration_seconds=conv.duration_seconds,
        segments=[
            {
                "id": s.id,
                "speaker_label": s.speaker_label,
                "start_time": s.start_time,
                "end_time": s.end_time,
                "text": s.text,
                "confidence": s.confidence,
                "sequence_index": s.sequence_index,
                "is_important": s.is_important,
                "importance_reason": s.importance_reason,
            }
            for s in segments
        ],
        speakers=[
            {
                "id": sp.id,
                "speaker_label": sp.speaker_label,
                "display_name": sp.display_name or sp.speaker_label,
                "role": sp.role,
            }
            for sp in speakers
        ],
        speaker_stats=_speaker_stats(segments),
    )


class SpeakerRenameRequest(BaseModel):
    renames: dict[str, str]  # current transcript label -> new name


@router.patch("/{conversation_id}/speaker-labels", response_model=TranscriptResponse)
async def rename_speakers(
    conversation_id: str,
    payload: SpeakerRenameRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Rename speakers across the transcript, e.g. "Speaker 1" -> "Dana (Customer)".

    Speech-to-text can't always tell voices apart, so this lets people correct labels.
    """
    conv = (await db.execute(
        select(Conversation).where(Conversation.id == conversation_id, *conversation_scope(current_user))
    )).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    renames = {old.strip(): new.strip()[:50] for old, new in payload.renames.items() if old.strip() and new.strip()}
    if not renames:
        raise HTTPException(status_code=400, detail="Give at least one speaker to rename")

    segments = (await db.execute(
        select(TranscriptSegment).where(TranscriptSegment.conversation_id == conversation_id)
    )).scalars().all()
    for seg in segments:
        if seg.speaker_label in renames:
            seg.speaker_label = renames[seg.speaker_label]
    speakers = (await db.execute(select(Speaker).where(Speaker.conversation_id == conversation_id))).scalars().all()
    for sp in speakers:
        current = sp.display_name or sp.speaker_label
        if current in renames:
            sp.display_name = renames[current]

    db.add(AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="rename_speakers",
        resource_type="conversation",
        resource_id=conversation_id,
        details={"renames": renames},
    ))
    await db.commit()
    return await get_transcript(conversation_id, current_user, db)


@router.get("/{conversation_id}/insights", response_model=InsightsResponse)
async def get_insights(
    conversation_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get all AI-generated insights for a conversation."""
    # Verify ownership
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            *conversation_scope(current_user),
        )
    )
    if not conv_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Load all insights
    async def _first(model, **kwargs):
        result = await db.execute(select(model).where(*[getattr(model, k) == v for k, v in kwargs.items()]))
        return result.scalar_one_or_none()

    async def _list(model, **kwargs):
        result = await db.execute(select(model).where(*[getattr(model, k) == v for k, v in kwargs.items()]))
        return result.scalars().all()

    summary = await _first(Summary, conversation_id=conversation_id)
    sentiment = await _first(SentimentResult, conversation_id=conversation_id)
    intent = await _first(IntentResult, conversation_id=conversation_id)
    sales = await _first(SalesInsight, conversation_id=conversation_id)
    minutes = await _first(MeetingMinutes, conversation_id=conversation_id)
    action_items = await _list(ActionItem, conversation_id=conversation_id)
    objections = await _list(Objection, conversation_id=conversation_id)
    recommendations = await _list(Recommendation, conversation_id=conversation_id)

    from app.db.models import Entity, PainPoint, AgentScore
    entities = await _list(Entity, conversation_id=conversation_id)
    pain_points = await _list(PainPoint, conversation_id=conversation_id)
    agent_score = await _first(AgentScore, conversation_id=conversation_id)

    def _summary_dict(s):
        if not s:
            return None
        return {
            "executive_summary": s.executive_summary,
            "detailed_summary": s.detailed_summary,
            "key_topics": s.key_topics,
            "decisions": s.decisions,
            "important_moments": s.important_moments,
            "open_questions": s.open_questions,
            "next_steps": s.next_steps,
        }

    def _sentiment_dict(s):
        if not s:
            return None
        return {
            "overall_sentiment": s.overall_sentiment,
            "overall_score": s.overall_score,
            "customer_sentiment": s.customer_sentiment,
            "agent_sentiment": s.agent_sentiment,
            "sentiment_trend": s.sentiment_trend,
            "timeline": s.timeline,
            "positive_moments": s.positive_moments,
            "negative_moments": s.negative_moments,
            "frustration_detected": s.frustration_detected,
            "satisfaction_detected": s.satisfaction_detected,
        }

    def _intent_dict(i):
        if not i:
            return None
        return {
            "primary_intent": i.primary_intent,
            "secondary_intents": i.secondary_intents,
            "confidence": i.confidence,
            "evidence": i.evidence,
        }

    def _sales_dict(s):
        if not s:
            return None
        return {
            "lead_score": s.lead_score,
            "purchase_intent": s.purchase_intent,
            "deal_health": s.deal_health,
            "budget_discussed": s.budget_discussed,
            "budget_range": s.budget_range,
            "decision_maker_present": s.decision_maker_present,
            "timeline_discussed": s.timeline_discussed,
            "timeline": s.timeline,
            "buying_signals": s.buying_signals,
            "upsell_opportunities": s.upsell_opportunities,
            "cross_sell_opportunities": s.cross_sell_opportunities,
            "stage": s.stage,
            "closing_probability": s.closing_probability,
        }

    return InsightsResponse(
        conversation_id=conversation_id,
        summary=_summary_dict(summary),
        sentiment=_sentiment_dict(sentiment),
        intent=_intent_dict(intent),
        sales_insight=_sales_dict(sales),
        action_items=[
            {
                "id": a.id, "description": a.description, "owner": a.owner,
                "due_date": a.due_date, "priority": a.priority, "status": a.status,
                "source_timestamp": a.source_timestamp, "related_topic": a.related_topic,
            }
            for a in action_items
        ],
        objections=[
            {
                "id": o.id, "category": o.category, "description": o.description,
                "exact_quote": o.exact_quote, "timestamp": o.timestamp,
                "severity": o.severity, "was_resolved": o.was_resolved,
                "suggested_response": o.suggested_response,
            }
            for o in objections
        ],
        entities=[
            {
                "id": e.id, "type": e.entity_type, "value": e.value,
                "context": e.context, "timestamp": e.timestamp,
                "sentiment": e.sentiment, "mention_count": e.mention_count,
            }
            for e in entities
        ],
        pain_points=[
            {
                "id": p.id, "category": p.category, "description": p.description,
                "severity": p.severity, "desired_outcome": p.desired_outcome,
                "potential_solution": p.potential_solution, "evidence": p.evidence,
            }
            for p in pain_points
        ],
        recommendations=[
            {
                "id": r.id, "category": r.category, "action": r.action,
                "reasoning": r.reasoning, "priority": r.priority,
                "urgency": r.urgency, "evidence": r.evidence,
            }
            for r in recommendations
        ],
        meeting_minutes={
            "objective": minutes.objective,
            "participants_summary": minutes.participants_summary,
            "discussion_points": minutes.discussion_points,
            "decisions": minutes.decisions,
            "action_items_summary": minutes.action_items_summary,
            "open_questions": minutes.open_questions,
            "risks": minutes.risks,
            "next_steps": minutes.next_steps,
            "next_meeting": minutes.next_meeting,
            "formatted_markdown": minutes.formatted_markdown,
        } if minutes else None,
        agent_score={
            "overall_score": agent_score.overall_score,
            "greeting_score": agent_score.greeting_score,
            "professionalism_score": agent_score.professionalism_score,
            "empathy_score": agent_score.empathy_score,
            "listening_score": agent_score.listening_score,
            "question_quality_score": agent_score.question_quality_score,
            "product_knowledge_score": agent_score.product_knowledge_score,
            "objection_handling_score": agent_score.objection_handling_score,
            "closing_score": agent_score.closing_score,
            "talk_ratio": agent_score.talk_ratio,
            "strengths": agent_score.strengths,
            "weaknesses": agent_score.weaknesses,
            "improvement_suggestions": agent_score.improvement_suggestions,
            "coaching_notes": agent_score.coaching_notes,
            "disclaimer": agent_score.disclaimer,
        } if agent_score else None,
    )


@router.get("/{conversation_id}/processing-status")
async def get_processing_status(
    conversation_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Poll processing status for a conversation."""
    # Verify ownership
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            *conversation_scope(current_user),
        )
    )
    conv = conv_result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Progress written by the worker; the cached copy saves a query on every 2.5 s poll
    from app.core.cache import get_job_status

    cached_status = await get_job_status(conversation_id)
    if cached_status and cached_status.get("conversation_status") == conv.status:
        return {"conversation_id": conversation_id, **cached_status}

    # Get latest job
    job_result = await db.execute(
        select(ProcessingJob)
        .where(ProcessingJob.conversation_id == conversation_id)
        .order_by(ProcessingJob.created_at.desc())
        .limit(1)
    )
    job = job_result.scalar_one_or_none()

    return {
        "conversation_id": conversation_id,
        "conversation_status": conv.status,
        "job": {
            "id": job.id if job else None,
            "status": job.status if job else None,
            "progress": job.progress if job else 0,
            "current_step": job.current_step if job else None,
            "error_message": job.error_message if job else None,
        } if job else None,
    }


@router.delete("/{conversation_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_conversation(
    conversation_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a conversation and all associated data."""
    import uuid

    result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            *conversation_scope(current_user),
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Delete file if it exists
    if conv.file_path and os.path.exists(conv.file_path):
        os.remove(conv.file_path)

    await db.execute(sa_delete(CRMRecord).where(CRMRecord.conversation_id == conversation_id))
    await db.delete(conv)

    db.add(AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="delete",
        resource_type="conversation",
        resource_id=conversation_id,
    ))

    await db.commit()
    await vector_store.delete_by_conversation(conversation_id)
    logger.info("Conversation deleted", conv_id=conversation_id, user_id=current_user.id)


@router.post("/{conversation_id}/reprocess", response_model=UploadResponse)
async def reprocess_conversation(
    conversation_id: str,
    background_tasks: BackgroundTasks,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Clear a conversation's transcript and insights and run the whole pipeline again.

    Useful after a failure, or after switching from mock to real AI providers.
    """
    conv = (await db.execute(
        select(Conversation)
        .options(
            selectinload(Conversation.speakers), selectinload(Conversation.transcript_segments),
            selectinload(Conversation.summary), selectinload(Conversation.sentiment),
            selectinload(Conversation.intent_result), selectinload(Conversation.sales_insight),
            selectinload(Conversation.action_items), selectinload(Conversation.objections),
            selectinload(Conversation.entities), selectinload(Conversation.pain_points),
            selectinload(Conversation.meeting_minutes), selectinload(Conversation.recommendations),
            selectinload(Conversation.agent_score),
        )
        .where(Conversation.id == conversation_id, *conversation_scope(current_user))
    )).scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")
    if conv.status in ("queued", "processing", "transcribing", "analyzing"):
        raise HTTPException(status_code=409, detail="This conversation is already being processed")
    if not conv.file_path or not os.path.exists(conv.file_path):
        raise HTTPException(status_code=409, detail="The original recording is no longer stored, so it can't be reprocessed")

    # Drop previous results (delete-orphan cascades remove the rows)
    conv.transcript_segments = []
    conv.speakers = []
    conv.summary = None
    conv.sentiment = None
    conv.intent_result = None
    conv.sales_insight = None
    conv.action_items = []
    conv.objections = []
    conv.entities = []
    conv.pain_points = []
    conv.meeting_minutes = None
    conv.recommendations = []
    conv.agent_score = None
    await db.execute(sa_delete(CRMRecord).where(CRMRecord.conversation_id == conversation_id, CRMRecord.status == "pending"))
    conv.status = "queued"
    conv.error_message = None

    job_id = str(uuid.uuid4())
    db.add(ProcessingJob(
        id=job_id, conversation_id=conversation_id, job_type="reprocess",
        status="queued", progress=0, current_step="Queued",
    ))
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="reprocess",
        resource_type="conversation",
        resource_id=conversation_id,
    ))
    await db.commit()
    await vector_store.delete_by_conversation(conversation_id)
    await _enqueue(db, background_tasks, conversation_id, job_id, conv.file_path)

    return UploadResponse(
        conversation_id=conversation_id,
        job_id=job_id,
        title=conv.title,
        status="queued",
        message="Reprocessing has started.",
    )
