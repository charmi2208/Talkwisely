"""
Conversation Processing Celery Tasks.

These tasks run as background jobs so that the API can return immediately
when a user uploads a file. The task progresses through:

1. Validate audio file
2. Normalize audio (if needed)
3. Run Speech-to-Text
4. Store transcript segments
5. Run LangGraph AI pipeline
6. Store all AI results in PostgreSQL
7. Generate embeddings
8. Send completion notification
"""

import asyncio
from datetime import datetime

from celery import Task
from celery.utils.log import get_task_logger
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.workers.celery_app import celery_app
from app.core.config import settings

logger = get_task_logger(__name__)


def _get_sync_db():
    """Create a synchronous database session for use inside Celery tasks."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker

    engine = create_engine(settings.database_sync_url)
    SessionLocal = sessionmaker(bind=engine)
    return SessionLocal()


def _update_job_status(db: Session, job_id: str, status: str, progress: int, step: str = "") -> None:
    """Update the processing job status in the database."""
    from app.db.models import ProcessingJob
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if job:
        job.status = status
        job.progress = progress
        job.current_step = step
        if status in ("completed", "failed"):
            job.completed_at = datetime.utcnow()
        db.commit()


def _update_conversation_status(db: Session, conversation_id: str, status: str, error: str = "") -> None:
    """Update the parent conversation's status."""
    from app.db.models import Conversation
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv:
        conv.status = status
        if error:
            conv.error_message = error
        db.commit()


@celery_app.task(bind=True, name="app.workers.conversation_tasks.process_conversation")
def process_conversation(self: Task, conversation_id: str, job_id: str, file_path: str) -> dict:
    """
    Main conversation processing pipeline.

    Called after a file is uploaded. Runs the full pipeline:
    STT → AI agents → DB storage → Embedding generation.
    """
    logger.info(f"Starting conversation processing: {conversation_id}")
    db = _get_sync_db()

    try:
        # Update initial status
        _update_job_status(db, job_id, "processing", 5, "Starting")
        _update_conversation_status(db, conversation_id, "processing")

        # ---- Run async pipeline in sync context ----
        result = asyncio.run(
            _async_process_conversation(conversation_id, job_id, file_path, db)
        )

        return result

    except Exception as e:
        logger.error(f"Conversation processing failed: {conversation_id} — {e}")
        error_msg = str(e)
        _update_job_status(db, job_id, "failed", 0, "Failed")
        _update_conversation_status(db, conversation_id, "failed", error=error_msg)

        # Create failure notification
        try:
            _create_failure_notification(db, conversation_id, error_msg)
        except Exception:
            pass

        raise

    finally:
        db.close()


def run_conversation_pipeline_direct(conversation_id: str, job_id: str, file_path: str) -> dict:
    """Run pipeline directly in background thread without Celery wrapper."""
    logger.info(f"Starting direct background conversation processing: {conversation_id}")
    db = _get_sync_db()
    try:
        _update_job_status(db, job_id, "processing", 5, "Starting")
        _update_conversation_status(db, conversation_id, "processing")
        result = asyncio.run(_async_process_conversation(conversation_id, job_id, file_path, db))
        return result
    except Exception as e:
        logger.error(f"Conversation processing failed: {conversation_id} — {e}")
        error_msg = str(e)
        _update_job_status(db, job_id, "failed", 0, "Failed")
        _update_conversation_status(db, conversation_id, "failed", error=error_msg)
        try:
            _create_failure_notification(db, conversation_id, error_msg)
        except Exception:
            pass
        return {}
    finally:
        db.close()


async def _async_process_conversation(
    conversation_id: str, job_id: str, file_path: str, db
) -> dict:
    """Async implementation of the conversation processing pipeline."""
    from app.ai.pipeline.graph import ConversationPipeline, get_llm_provider, get_stt_provider
    from app.db.models import (
        ActionItem, AgentScore, Conversation, CRMRecord, Entity, IntentResult,
        MeetingMinutes, Notification, Objection, PainPoint, ProcessingJob,
        Recommendation, SalesInsight, SentimentResult, Speaker, Summary, TranscriptSegment, User
    )

    def update(status: str, progress: int, step: str) -> None:
        _update_job_status(db, job_id, status, progress, step)

    # ---- Step 1: Transcription ----
    update("processing", 10, "Transcribing audio")
    _update_conversation_status(db, conversation_id, "transcribing")

    stt = get_stt_provider()
    transcript_result = await stt.transcribe(file_path, diarize=True)

    # Convert STT segments to pipeline format
    raw_segments = []
    for i, seg in enumerate(transcript_result.segments):
        raw_segments.append({
            "speaker": seg.speaker,
            "speaker_label": seg.speaker,  # Will be updated in clean step
            "start": seg.start,
            "end": seg.end,
            "text": seg.text,
            "confidence": seg.confidence,
            "sequence_index": i,
        })

    # Update conversation with duration
    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conv:
        conv.duration_seconds = int(transcript_result.duration)
        conv.language = transcript_result.language
        conv.status = "analyzing"
        db.commit()

    # ---- Step 2: Save transcript to DB ----
    update("processing", 30, "Saving transcript")

    # Create speakers
    speaker_db_map: dict[str, str] = {}  # speaker_label -> Speaker.id
    unique_speakers = {}
    for seg in raw_segments:
        s = seg["speaker"]
        if s not in unique_speakers:
            idx = len(unique_speakers) + 1
            unique_speakers[s] = f"Speaker {idx}"

    for raw_label, display_name in unique_speakers.items():
        from app.db.models import Speaker as SpeakerModel
        import uuid as uuid_mod
        speaker = SpeakerModel(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            speaker_label=raw_label,
            display_name=display_name,
        )
        db.add(speaker)
        db.flush()
        speaker_db_map[raw_label] = speaker.id

    # Create transcript segments
    import uuid as uuid_mod
    for seg in raw_segments:
        ts = TranscriptSegment(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            speaker_id=speaker_db_map.get(seg["speaker"]),
            speaker_label=unique_speakers.get(seg["speaker"], "Speaker 1"),
            start_time=seg["start"],
            end_time=seg["end"],
            text=seg["text"],
            confidence=seg.get("confidence"),
            sequence_index=seg["sequence_index"],
        )
        db.add(ts)

    db.commit()

    # ---- Step 3: AI Pipeline ----
    update("processing", 35, "Running AI analysis")
    _update_conversation_status(db, conversation_id, "analyzing")

    llm = get_llm_provider()
    pipeline = ConversationPipeline(llm)

    async def on_step_callback(step_name: str, pct: int) -> None:
        update("processing", 35 + int(pct * 0.55), step_name)

    pipeline_state = await pipeline.run(
        conversation_id=conversation_id,
        organization_id=conv.organization_id if conv else "",
        raw_segments=raw_segments,
        full_transcript_text=transcript_result.full_text,
        language=transcript_result.language,
        duration_seconds=transcript_result.duration,
        audio_file_path=file_path,
        on_step=on_step_callback,
    )

    # ---- Step 4: Store AI results ----
    update("processing", 90, "Storing AI results")

    # Store Summary
    if pipeline_state.get("executive_summary"):
        summary = Summary(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            executive_summary=pipeline_state.get("executive_summary", ""),
            detailed_summary=pipeline_state.get("detailed_summary", ""),
            key_topics=pipeline_state.get("key_topics", []),
            decisions=pipeline_state.get("decisions", []),
            important_moments=pipeline_state.get("important_moments", []),
            open_questions=pipeline_state.get("open_questions", []),
            next_steps=pipeline_state.get("next_steps", []),
        )
        db.add(summary)

    # Store Sentiment
    if pipeline_state.get("overall_sentiment"):
        sentiment = SentimentResult(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            overall_sentiment=pipeline_state.get("overall_sentiment", "neutral"),
            overall_score=pipeline_state.get("overall_sentiment_score", 0.0),
            customer_sentiment=pipeline_state.get("customer_sentiment"),
            agent_sentiment=pipeline_state.get("agent_sentiment"),
            sentiment_trend=pipeline_state.get("sentiment_trend"),
            timeline=pipeline_state.get("sentiment_timeline", []),
            positive_moments=pipeline_state.get("positive_moments", []),
            negative_moments=pipeline_state.get("negative_moments", []),
            frustration_detected=pipeline_state.get("frustration_detected", False),
            satisfaction_detected=pipeline_state.get("satisfaction_detected", False),
        )
        db.add(sentiment)

    # Store Intent
    if pipeline_state.get("primary_intent"):
        intent = IntentResult(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            primary_intent=pipeline_state.get("primary_intent", ""),
            secondary_intents=pipeline_state.get("secondary_intents", []),
            confidence=pipeline_state.get("intent_confidence"),
            evidence=pipeline_state.get("intent_evidence", []),
        )
        db.add(intent)

    # Store Sales Insight
    if pipeline_state.get("lead_score") is not None:
        sales = SalesInsight(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            lead_score=pipeline_state.get("lead_score"),
            purchase_intent=pipeline_state.get("purchase_intent"),
            deal_health=pipeline_state.get("deal_health"),
            budget_discussed=pipeline_state.get("budget_discussed", False),
            budget_range=pipeline_state.get("budget_range"),
            decision_maker_present=pipeline_state.get("decision_maker_present", False),
            timeline_discussed=pipeline_state.get("timeline_discussed", False),
            timeline=pipeline_state.get("deal_timeline"),
            buying_signals=pipeline_state.get("buying_signals", []),
            upsell_opportunities=pipeline_state.get("upsell_opportunities", []),
            cross_sell_opportunities=pipeline_state.get("cross_sell_opportunities", []),
            stage=pipeline_state.get("pipeline_stage"),
            closing_probability=pipeline_state.get("closing_probability"),
        )
        db.add(sales)

    # Store Action Items
    org_id = conv.organization_id if conv else ""
    for ai_item in pipeline_state.get("action_items", []):
        action = ActionItem(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            organization_id=org_id,
            description=ai_item.get("description", ""),
            owner=ai_item.get("owner"),
            owner_speaker_label=ai_item.get("owner_speaker"),
            due_date=ai_item.get("due_date"),
            priority=ai_item.get("priority", "medium"),
            source_timestamp=ai_item.get("timestamp"),
            related_topic=ai_item.get("related_topic"),
        )
        db.add(action)

    # Store Objections
    for obj in pipeline_state.get("objections", []):
        objection = Objection(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            category=obj.get("category", "other"),
            description=obj.get("description", ""),
            exact_quote=obj.get("exact_quote"),
            timestamp=obj.get("timestamp"),
            severity=obj.get("severity", "medium"),
            was_resolved=bool(obj.get("was_resolved", False)),
            suggested_response=obj.get("suggested_response"),
        )
        db.add(objection)

    # Store Entities
    for ent in pipeline_state.get("entities", []):
        entity = Entity(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            entity_type=ent.get("type", "other"),
            value=ent.get("value", ""),
            context=ent.get("context"),
            timestamp=ent.get("timestamp"),
            sentiment=ent.get("sentiment"),
            mention_count=int(ent.get("mention_count", 1)),
        )
        db.add(entity)

    # Store Pain Points
    for pp in pipeline_state.get("pain_points", []):
        pain = PainPoint(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            category=pp.get("category", "other"),
            description=pp.get("description", ""),
            severity=pp.get("severity", "medium"),
            desired_outcome=pp.get("desired_outcome"),
            potential_solution=pp.get("potential_solution"),
            evidence=pp.get("evidence"),
            timestamp=pp.get("timestamp"),
        )
        db.add(pain)

    # Store Meeting Minutes
    minutes_data = pipeline_state.get("meeting_minutes")
    if minutes_data:
        minutes = MeetingMinutes(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            objective=minutes_data.get("objective"),
            participants_summary=minutes_data.get("participants_summary"),
            discussion_points=minutes_data.get("discussion_points", []),
            decisions=minutes_data.get("decisions", []),
            action_items_summary=minutes_data.get("action_items_summary", []),
            open_questions=minutes_data.get("open_questions", []),
            risks=minutes_data.get("risks", []),
            next_steps=minutes_data.get("next_steps", []),
            next_meeting=minutes_data.get("next_meeting"),
            formatted_markdown=minutes_data.get("formatted_markdown"),
        )
        db.add(minutes)

    # Store Recommendations
    for rec in pipeline_state.get("recommendations", []):
        recommendation = Recommendation(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            category=rec.get("category", "other"),
            action=rec.get("action", ""),
            reasoning=rec.get("reasoning"),
            priority=rec.get("priority", "medium"),
            urgency=rec.get("urgency", "normal"),
            evidence=rec.get("evidence", []),
        )
        db.add(recommendation)

    # Store CRM Proposals
    crm_data = pipeline_state.get("crm_proposed_changes")
    if crm_data and crm_data.get("proposed_changes"):
        crm_record = CRMRecord(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            organization_id=org_id,
            crm_entity_type=crm_data.get("crm_entity_type", "lead"),
            proposed_changes=crm_data.get("proposed_changes", {}),
            status="pending",
        )
        db.add(crm_record)

    # Store Agent Score
    score_data = pipeline_state.get("agent_score")
    if score_data:
        agent_score = AgentScore(
            id=str(uuid_mod.uuid4()),
            conversation_id=conversation_id,
            overall_score=score_data.get("overall_score"),
            greeting_score=score_data.get("greeting_score"),
            professionalism_score=score_data.get("professionalism_score"),
            empathy_score=score_data.get("empathy_score"),
            listening_score=score_data.get("listening_score"),
            question_quality_score=score_data.get("question_quality_score"),
            product_knowledge_score=score_data.get("product_knowledge_score"),
            objection_handling_score=score_data.get("objection_handling_score"),
            closing_score=score_data.get("closing_score"),
            talk_ratio=score_data.get("talk_ratio"),
            interruption_count=score_data.get("interruption_count"),
            filler_word_count=score_data.get("filler_word_count"),
            strengths=score_data.get("strengths", []),
            weaknesses=score_data.get("weaknesses", []),
            improvement_suggestions=score_data.get("improvement_suggestions", []),
            coaching_notes=score_data.get("coaching_notes"),
            disclaimer=score_data.get("disclaimer", "AI-generated assessment"),
        )
        db.add(agent_score)

    # Update conversation type from pipeline
    if conv:
        conv.conversation_type = pipeline_state.get("conversation_type", "general_business")
        conv.status = "completed"

    # Update processing job
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    if job:
        job.status = "completed"
        job.progress = 100
        job.current_step = "Complete"
        job.completed_at = datetime.utcnow()

    db.commit()

    # Send completion notification
    await _create_completion_notification_async(db, conversation_id)

    logger.info(f"Conversation processing complete: {conversation_id}")
    return {"status": "completed", "conversation_id": conversation_id}


async def _create_completion_notification_async(db, conversation_id: str) -> None:
    """Create an in-app notification for processing completion."""
    from app.db.models import Conversation, Notification
    import uuid as uuid_mod

    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return

    notification = Notification(
        id=str(uuid_mod.uuid4()),
        user_id=conv.created_by,
        conversation_id=conversation_id,
        type="processing_complete",
        title="Analysis Complete",
        message=f'"{conv.title}" has been analyzed. View insights now.',
    )
    db.add(notification)
    db.commit()


def _create_failure_notification(db, conversation_id: str, error: str) -> None:
    """Create an in-app notification for processing failure."""
    from app.db.models import Conversation, Notification
    import uuid as uuid_mod

    conv = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conv:
        return

    notification = Notification(
        id=str(uuid_mod.uuid4()),
        user_id=conv.created_by,
        conversation_id=conversation_id,
        type="processing_failed",
        title="Processing Failed",
        message=f'"{conv.title}" could not be processed. Please try uploading again.',
    )
    db.add(notification)
    db.commit()
