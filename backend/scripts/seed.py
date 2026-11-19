"""
Database Seed Script for TalkWiseAI.

Creates complete demo data including:
- Demo organization
- Demo users (admin, manager, agent)
- Pre-built roles
- Sample conversations with complete AI insights
- Action items, notifications, analytics data

Run: python scripts/seed.py
"""

import asyncio
import sys
import uuid
from datetime import datetime, timedelta
from pathlib import Path

# Add backend root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from app.core.config import settings
from app.core.security import hash_password
from app.db.models import (
    ActionItem, AgentScore, AuditLog, CRMRecord, Conversation,
    Entity, Integration, IntentResult, KnowledgeChunk, KnowledgeDocument,
    MeetingMinutes, Notification, Objection, Organization,
    PainPoint, Participant, ProcessingJob, Recommendation,
    Role, SalesInsight, SentimentResult, Speaker, Summary,
    TranscriptSegment, User, UserRole
)


# ---------------------------------------------------------------------------
# Demo content (see scripts/demo_data.py)
# ---------------------------------------------------------------------------

from scripts.demo_data import CONVERSATIONS, KNOWLEDGE_DOCUMENTS  # noqa: E402

DEMO_FILE_PREFIX = "demo-"            # file_name of seeded conversations: demo-<key>.mp3
LEGACY_DEMO_FILE_NAME = "demo_recording.mp3"  # placeholder conversations from older seeds
WORDS_PER_SECOND = 2.6


def _timings(transcript: list[tuple[str, str]]) -> list[tuple[float, float]]:
    """Start and end time of each turn from its length (about 2.6 words per second)."""
    times, start = [], 0.0
    for _, text in transcript:
        end = start + max(2.5, len(text.split()) / WORDS_PER_SECOND)
        times.append((round(start, 1), round(end, 1)))
        start = end + 0.7
    return times


def _quote(transcript, turn: int) -> str:
    return transcript[turn][1]


def _due(days_from_today: int) -> datetime:
    return (datetime.utcnow() + timedelta(days=days_from_today)).replace(hour=17, minute=0, second=0, microsecond=0)


def _minutes_markdown(m: dict) -> str:
    lines = ["# Meeting Minutes", "", "## Objective", m["objective"], "", "## Participants", m["participants"], "", "## Discussion Points"]
    lines += [f"- {p}" for p in m["points"]]
    for heading, key, prefix in (("Decisions", "decisions", "- "), ("Action Items", "actions", "- [ ] "),
                                 ("Open Questions", "questions", "- "), ("Risks", "risks", "- ")):
        lines += ["", f"## {heading}"] + ([f"{prefix}{x}" for x in m[key]] or ["- None"])
    if m.get("next_meeting"):
        lines += ["", "## Next Meeting", m["next_meeting"]]
    return "\n".join(lines)


def _remove_demo_conversations(db, organization_id: str) -> int:
    """Delete conversations created by this seed (or older placeholder seeds), never uploads."""
    from sqlalchemy import or_

    convs = db.query(Conversation).filter(
        Conversation.organization_id == organization_id,
        or_(Conversation.file_name == LEGACY_DEMO_FILE_NAME, Conversation.file_name.like(f"{DEMO_FILE_PREFIX}%")),
    ).all()
    ids = [c.id for c in convs]
    if ids:
        db.query(CRMRecord).filter(CRMRecord.conversation_id.in_(ids)).delete(synchronize_session=False)
    for conv in convs:
        db.delete(conv)
    db.flush()
    if ids:
        try:
            from app.ai.rag.vector_store import vector_store

            async def purge():
                for conv_id in ids:
                    await vector_store.delete_by_conversation(conv_id)

            asyncio.run(purge())
        except Exception as e:  # the next reindex rebuilds what's missing
            print(f"  (search index cleanup skipped: {e})")
    return len(ids)


def _add_conversation(db, org_id: str, users: dict, demo: dict) -> None:
    """Create one demo conversation with transcript, speakers and every insight table."""
    transcript = demo["transcript"]
    times = _timings(transcript)
    at = lambda turn: times[turn][0]  # noqa: E731
    occurred = (datetime.utcnow() - timedelta(days=demo["days_ago"])).replace(hour=demo["hour"], minute=0, second=0, microsecond=0)
    duration = int(round(times[-1][1]))
    owner = users[demo["owner"]]
    conv_id = str(uuid.uuid4())

    db.add(Conversation(
        id=conv_id, organization_id=org_id, created_by=owner.id, title=demo["title"],
        conversation_type=demo["type"], status="completed", duration_seconds=duration, language="en",
        file_name=f"{DEMO_FILE_PREFIX}{demo['key']}.mp3", occurred_at=occurred, created_at=occurred,
        extra_metadata={"demo_seed": True},
    ))
    db.flush()
    db.add(ProcessingJob(
        id=str(uuid.uuid4()), conversation_id=conv_id, job_type="full_pipeline", status="completed", progress=100,
        current_step="Complete", started_at=occurred, completed_at=occurred + timedelta(minutes=1), created_at=occurred,
    ))

    # Participants, speakers and transcript
    talk: dict[str, float] = {}
    words: dict[str, int] = {}
    for (speaker, text), (start, end) in zip(transcript, times):
        talk[speaker] = talk.get(speaker, 0.0) + (end - start)
        words[speaker] = words.get(speaker, 0) + len(text.split())
    speaker_ids = {}
    for name, (role, is_agent) in demo["speakers"].items():
        db.add(Participant(id=str(uuid.uuid4()), conversation_id=conv_id, name=name, role=role, is_agent=is_agent))
        speaker_ids[name] = str(uuid.uuid4())
        db.add(Speaker(
            id=speaker_ids[name], conversation_id=conv_id, speaker_label=name, display_name=name, role=role,
            talk_time_seconds=round(talk.get(name, 0.0), 1), word_count=words.get(name, 0),
        ))
    important = {turn for turn, _ in demo["summary"]["moments"]}
    for idx, ((speaker, text), (start, end)) in enumerate(zip(transcript, times)):
        db.add(TranscriptSegment(
            id=str(uuid.uuid4()), conversation_id=conv_id, speaker_id=speaker_ids.get(speaker), speaker_label=speaker,
            start_time=start, end_time=end, text=text, confidence=0.95, sequence_index=idx,
            is_important=idx in important,
        ))

    s = demo["summary"]
    db.add(Summary(
        id=str(uuid.uuid4()), conversation_id=conv_id, executive_summary=s["executive"], detailed_summary=s["detailed"],
        key_topics=s["topics"], decisions=s["decisions"],
        important_moments=[{"timestamp": at(t), "description": d} for t, d in s["moments"]],
        open_questions=s["questions"], next_steps=s["next_steps"],
    ))

    se = demo["sentiment"]
    db.add(SentimentResult(
        id=str(uuid.uuid4()), conversation_id=conv_id, overall_sentiment=se["overall"], overall_score=se["score"],
        customer_sentiment=se["customer"], agent_sentiment=se["agent"], sentiment_trend=se["trend"],
        timeline=[{"timestamp": at(t), "speaker": who, "sentiment": label, "score": score} for t, who, label, score in se["timeline"]],
        positive_moments=[{"timestamp": at(t), "description": d} for t, d in se["positive"]],
        negative_moments=[{"timestamp": at(t), "description": d} for t, d in se["negative"]],
        frustration_detected=se["overall"] == "negative", satisfaction_detected=se["overall"] == "positive",
    ))

    it = demo["intent"]
    db.add(IntentResult(
        id=str(uuid.uuid4()), conversation_id=conv_id, primary_intent=it["primary"], secondary_intents=it["secondary"],
        confidence=it["confidence"], evidence=[{"text": _quote(transcript, t), "timestamp": at(t)} for t in it["evidence"]],
    ))

    sales = demo["sales"]
    if sales:
        db.add(SalesInsight(
            id=str(uuid.uuid4()), conversation_id=conv_id, lead_score=sales["lead_score"],
            purchase_intent=sales["purchase_intent"], deal_health=sales["deal_health"],
            budget_discussed=sales["budget_range"] is not None, budget_range=sales["budget_range"],
            decision_maker_present=sales["decision_maker"], timeline_discussed=sales["timeline"] is not None,
            timeline=sales["timeline"],
            buying_signals=[{"signal": sig, "timestamp": at(t), "evidence": _quote(transcript, t)} for sig, t in sales["signals"]],
            upsell_opportunities=sales["upsell"], cross_sell_opportunities=sales["cross_sell"],
            stage=sales["stage"], closing_probability=sales["closing_probability"],
        ))

    for desc, who, due_text, due_days, priority, status_val, turn in demo["actions"]:
        db.add(ActionItem(
            id=str(uuid.uuid4()), conversation_id=conv_id, organization_id=org_id, description=desc, owner=who,
            due_date=due_text, due_date_parsed=_due(due_days), priority=priority, status=status_val,
            completed_at=occurred + timedelta(days=1) if status_val == "completed" else None,
            source_timestamp=at(turn), related_topic=s["topics"][0], created_at=occurred,
        ))

    for category, desc, turn, severity, resolved, response in demo["objections"]:
        db.add(Objection(
            id=str(uuid.uuid4()), conversation_id=conv_id, category=category, description=desc,
            exact_quote=_quote(transcript, turn), timestamp=at(turn), severity=severity,
            was_resolved=resolved, suggested_response=response,
        ))

    for etype, value, context, turn, sentiment, count in demo["entities"]:
        db.add(Entity(
            id=str(uuid.uuid4()), conversation_id=conv_id, entity_type=etype, value=value, context=context,
            timestamp=at(turn), sentiment=sentiment, mention_count=count,
        ))

    for category, desc, turn, severity, outcome, solution in demo["pain_points"]:
        db.add(PainPoint(
            id=str(uuid.uuid4()), conversation_id=conv_id, category=category, description=desc, severity=severity,
            desired_outcome=outcome, potential_solution=solution, evidence=_quote(transcript, turn), timestamp=at(turn),
        ))

    m = demo["minutes"]
    db.add(MeetingMinutes(
        id=str(uuid.uuid4()), conversation_id=conv_id, objective=m["objective"], participants_summary=m["participants"],
        discussion_points=m["points"], decisions=m["decisions"], action_items_summary=m["actions"],
        open_questions=m["questions"], risks=m["risks"], next_steps=s["next_steps"], next_meeting=m["next_meeting"],
        formatted_markdown=_minutes_markdown(m),
    ))

    for category, action, reasoning, priority, urgency, evidence_turns in demo["recommendations"]:
        db.add(Recommendation(
            id=str(uuid.uuid4()), conversation_id=conv_id, category=category, action=action, reasoning=reasoning,
            priority=priority, urgency=urgency, evidence=[_quote(transcript, t) for t in evidence_turns],
        ))

    score = demo["agent_score"]
    if score:
        greet, prof, emp, listen, question, product, objection, closing = score["dims"]
        db.add(AgentScore(
            id=str(uuid.uuid4()), conversation_id=conv_id, overall_score=score["overall"],
            greeting_score=greet, professionalism_score=prof, empathy_score=emp, listening_score=listen,
            question_quality_score=question, product_knowledge_score=product, objection_handling_score=objection,
            closing_score=closing, talk_ratio=score["talk_ratio"], interruption_count=0, filler_word_count=3,
            strengths=score["strengths"], weaknesses=score["weaknesses"], improvement_suggestions=score["suggestions"],
            coaching_notes=score["notes"],
            disclaimer="This is an AI-generated assessment and should be used as one input among many.",
        ))

    crm = demo["crm"]
    if crm:
        approver = users["manager"].id if crm["status"] in ("applied", "rejected") else None
        db.add(CRMRecord(
            id=str(uuid.uuid4()), conversation_id=conv_id, organization_id=org_id, crm_entity_type=crm["entity"],
            proposed_changes=crm["changes"], status=crm["status"],
            approved_by=approver if crm["status"] == "applied" else None,
            applied_at=occurred + timedelta(days=1) if crm["status"] == "applied" else None, created_at=occurred,
        ))


def _add_knowledge_documents(db, org_id: str, uploader_id: str) -> int:
    import os

    added = 0
    for doc in KNOWLEDGE_DOCUMENTS:
        if db.query(KnowledgeDocument).filter(
            KnowledgeDocument.organization_id == org_id, KnowledgeDocument.title == doc["title"]
        ).first():
            continue
        doc_id = str(uuid.uuid4())
        folder = os.path.join(settings.storage_local_path, "kb", org_id)
        os.makedirs(folder, exist_ok=True)
        path = os.path.join(folder, f"{doc_id}.md")
        with open(path, "w", encoding="utf-8") as f:
            f.write(doc["text"])
        paragraphs = [p.strip() for p in doc["text"].split("\n\n") if p.strip()]
        db.add(KnowledgeDocument(
            id=doc_id, organization_id=org_id, uploaded_by=uploader_id, title=doc["title"], file_name=doc["file_name"],
            file_path=path, file_type="md", file_size_bytes=len(doc["text"].encode()), category=doc["category"],
            status="indexed", chunk_count=len(paragraphs),
        ))
        for idx, text_chunk in enumerate(paragraphs):
            db.add(KnowledgeChunk(
                document_id=doc_id, organization_id=org_id, chunk_index=idx, text=text_chunk,
                vector_id=f"{doc_id}_chunk_{idx}", extra_metadata={"category": doc["category"], "title": doc["title"]},
            ))
        added += 1
    return added


def seed_database(refresh_demo: bool = False) -> None:
    """Create the demo organization, users and content (skips what already exists).

    ``refresh_demo`` first deletes previously seeded demo conversations (including the
    placeholder ones from older versions of this script), then seeds them again.
    Conversations people uploaded are never touched.
    """
    # Create or upgrade the schema the same way start.py does
    from app.db.migrate import upgrade_database

    upgrade_database(settings.database_sync_url)
    engine = create_engine(settings.database_sync_url, echo=False)

    SessionLocal = sessionmaker(bind=engine)
    db = SessionLocal()

    try:
        print("Starting database seed...")

        # ---- Roles ----
        print("Creating roles...")
        roles = {}
        for role_name, permissions in [
            ("admin", {"manage_org": True, "manage_users": True, "view_all": True, "configure": True}),
            ("manager", {"view_team": True, "view_conversations": True, "view_analytics": True}),
            ("agent", {"upload": True, "view_own": True, "use_ai": True}),
        ]:
            existing = db.query(Role).filter(Role.name == role_name).first()
            if not existing:
                role = Role(
                    id=str(uuid.uuid4()),
                    name=role_name,
                    description=f"{role_name.title()} role",
                    permissions=permissions,
                )
                db.add(role)
                roles[role_name] = role
            else:
                roles[role_name] = existing
        db.flush()

        # ---- Demo Organization ----
        print("Creating demo organization...")
        demo_org = db.query(Organization).filter(Organization.slug == "demo").first()
        if not demo_org:
            demo_org = Organization(
                id=str(uuid.uuid4()),
                name="TalkWiseAI Demo",
                slug="demo",
                plan="enterprise",
                is_active=True,
            )
            db.add(demo_org)
            db.flush()

        # ---- Demo Users ----
        print("Creating demo users...")
        users_data = [
            ("admin@demo.talkwiseai.com", "admin123", "Alex Thompson", "admin"),
            ("manager@demo.talkwiseai.com", "manager123", "Priya Sharma", "manager"),
            ("agent@demo.talkwiseai.com", "agent123", "James Wilson", "agent"),
            ("agent2@demo.talkwiseai.com", "agent123", "Sarah Chen", "agent"),
        ]

        demo_users = {}
        for email, password, full_name, role_name in users_data:
            existing = db.query(User).filter(User.email == email).first()
            if not existing:
                user = User(
                    id=str(uuid.uuid4()),
                    organization_id=demo_org.id,
                    email=email,
                    hashed_password=hash_password(password),
                    full_name=full_name,
                    is_active=True,
                    is_verified=True,
                    last_login_at=datetime.utcnow(),
                )
                db.add(user)
                db.flush()

                user_role = UserRole(
                    id=str(uuid.uuid4()),
                    user_id=user.id,
                    role_id=roles[role_name].id,
                )
                db.add(user_role)
                demo_users[email] = user
            else:
                demo_users[email] = existing

        db.flush()
        admin_user = demo_users["admin@demo.talkwiseai.com"]
        agent_user = demo_users["agent@demo.talkwiseai.com"]
        agent2_user = demo_users["agent2@demo.talkwiseai.com"]

        # ---- Mock Integration Setup ----
        for int_type, provider in [("crm", "mock"), ("calendar", "mock"), ("email", "mock"), ("talkwisely", "mock")]:
            existing = db.query(Integration).filter(
                Integration.organization_id == demo_org.id,
                Integration.integration_type == int_type,
            ).first()
            if not existing:
                db.add(Integration(
                    id=str(uuid.uuid4()),
                    organization_id=demo_org.id,
                    integration_type=int_type,
                    provider=provider,
                    is_enabled=True,
                    is_connected=True,
                    config={},  # registry defaults fill in on first read
                    last_synced_at=datetime.utcnow(),
                ))

        # ---- Demo conversations ----
        users = {
            "agent": agent_user,
            "agent2": agent2_user,
            "manager": demo_users["manager@demo.talkwiseai.com"],
            "admin": admin_user,
        }
        if refresh_demo:
            removed = _remove_demo_conversations(db, demo_org.id)
            print(f"Removed {removed} previously seeded demo conversation(s)")
        existing_titles = {t for (t,) in db.query(Conversation.title).filter(Conversation.organization_id == demo_org.id)}
        new = [demo for demo in CONVERSATIONS if demo["title"] not in existing_titles]
        print(f"Creating {len(new)} demo conversation(s)...")
        for demo in new:
            _add_conversation(db, demo_org.id, users, demo)

        docs = _add_knowledge_documents(db, demo_org.id, admin_user.id)
        if docs:
            print(f"Added {docs} knowledge-base document(s)")

        # ---- Notifications ----
        if new and not db.query(Notification).filter(Notification.user_id == agent_user.id).first():
            print("Creating sample notifications...")
            for notif_type, title, message in [
                ("processing_complete", "Analysis Complete", '"Enterprise Sales Call — Meridian Financial Group" has been analyzed. View insights now.'),
                ("high_intent", "High-intent lead detected", '"Enterprise Sales Call — Meridian Financial Group" scored 84/100. Review the recommended next steps.'),
                ("processing_complete", "Analysis Complete", '"Support Escalation — Omega Retail" has been analyzed. View insights now.'),
            ]:
                db.add(Notification(
                    id=str(uuid.uuid4()), user_id=agent_user.id, type=notif_type, title=title, message=message, is_read=False,
                ))

        db.commit()
        print("[SUCCESS] Database seeded successfully!")
        print("\nDemo Credentials:")
        print("  Admin: admin@demo.talkwiseai.com / admin123")
        print("  Manager: manager@demo.talkwiseai.com / manager123")
        print("  Agent: agent@demo.talkwiseai.com / agent123")

    except Exception as e:
        print(f"[ERROR] Seed failed: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        engine.dispose()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Load the demo organization, users and content.")
    parser.add_argument("--refresh-demo", action="store_true",
                        help="replace previously seeded demo conversations (uploads are kept)")
    seed_database(refresh_demo=parser.parse_args().refresh_demo)
