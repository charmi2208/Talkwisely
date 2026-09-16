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
    Entity, Integration, IntentResult, KnowledgeDocument,
    MeetingMinutes, Notification, Objection, Organization,
    PainPoint, Participant, ProcessingJob, Recommendation,
    Role, SalesInsight, SentimentResult, Speaker, Summary,
    TranscriptSegment, User, UserRole
)
from app.db.session import Base


# ---------------------------------------------------------------------------
# Sample conversations data
# ---------------------------------------------------------------------------

SAMPLE_CONVERSATIONS = [
    {
        "title": "Enterprise Sales Call — Meridian Financial Group",
        "type": "sales",
        "duration": 540,
        "lead_score": 82,
        "purchase_intent": "high",
        "deal_health": "healthy",
        "overall_sentiment": "positive",
        "agent_score": 84,
    },
    {
        "title": "Product Demo — TechCorp Solutions",
        "type": "product_demo",
        "duration": 2700,
        "lead_score": 71,
        "purchase_intent": "medium",
        "deal_health": "healthy",
        "overall_sentiment": "positive",
        "agent_score": 79,
    },
    {
        "title": "Support Escalation — Omega Retail",
        "type": "customer_support",
        "duration": 1260,
        "lead_score": None,
        "purchase_intent": None,
        "deal_health": None,
        "overall_sentiment": "negative",
        "agent_score": 65,
    },
    {
        "title": "Weekly Team Strategy Meeting",
        "type": "internal_meeting",
        "duration": 3600,
        "lead_score": None,
        "purchase_intent": None,
        "deal_health": None,
        "overall_sentiment": "neutral",
        "agent_score": None,
    },
    {
        "title": "Follow-up Call — BlueSky Logistics",
        "type": "follow_up",
        "duration": 900,
        "lead_score": 88,
        "purchase_intent": "high",
        "deal_health": "healthy",
        "overall_sentiment": "positive",
        "agent_score": 91,
    },
    {
        "title": "Initial Discovery — GreenField Manufacturing",
        "type": "sales",
        "duration": 1800,
        "lead_score": 55,
        "purchase_intent": "medium",
        "deal_health": "at_risk",
        "overall_sentiment": "neutral",
        "agent_score": 72,
    },
    {
        "title": "Customer Complaint — DataSync Inc",
        "type": "customer_support",
        "duration": 720,
        "lead_score": None,
        "purchase_intent": None,
        "deal_health": None,
        "overall_sentiment": "negative",
        "agent_score": 58,
    },
    {
        "title": "Renewal Discussion — Apex Consulting",
        "type": "sales",
        "duration": 1500,
        "lead_score": 93,
        "purchase_intent": "high",
        "deal_health": "healthy",
        "overall_sentiment": "positive",
        "agent_score": 88,
    },
]


def seed_database() -> None:
    """Main seed function — creates all demo data."""
    engine = create_engine(settings.database_sync_url, echo=False)

    # Create all tables
    Base.metadata.create_all(engine)

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
                    config={"note": "Mock integration for demo"},
                    last_synced_at=datetime.utcnow(),
                ))

        # ---- Sample Conversations ----
        print(f"Creating {len(SAMPLE_CONVERSATIONS)} sample conversations...")

        days_back = len(SAMPLE_CONVERSATIONS)
        for i, sample in enumerate(SAMPLE_CONVERSATIONS):
            existing = db.query(Conversation).filter(
                Conversation.title == sample["title"],
                Conversation.organization_id == demo_org.id,
            ).first()
            if existing:
                continue

            conv_id = str(uuid.uuid4())
            created_at = datetime.utcnow() - timedelta(days=(days_back - i), hours=i * 2)

            conv = Conversation(
                id=conv_id,
                organization_id=demo_org.id,
                created_by=agent_user.id,
                title=sample["title"],
                conversation_type=sample["type"],
                status="completed",
                duration_seconds=sample["duration"],
                language="en",
                file_name="demo_recording.mp3",
                occurred_at=created_at,
                created_at=created_at,
            )
            db.add(conv)
            db.flush()

            # Processing Job
            db.add(ProcessingJob(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                job_type="full_pipeline",
                status="completed",
                progress=100,
                current_step="Complete",
                started_at=created_at,
                completed_at=created_at + timedelta(minutes=2),
                created_at=created_at,
            ))

            # Speakers
            spk1_id = str(uuid.uuid4())
            spk2_id = str(uuid.uuid4())
            db.add(Speaker(
                id=spk1_id,
                conversation_id=conv_id,
                speaker_label="SPEAKER_00",
                display_name="Sales Representative",
                role="sales_rep",
                talk_time_seconds=sample["duration"] * 0.52,
            ))
            db.add(Speaker(
                id=spk2_id,
                conversation_id=conv_id,
                speaker_label="SPEAKER_01",
                display_name="Customer",
                role="customer",
                talk_time_seconds=sample["duration"] * 0.48,
            ))

            # Summary
            db.add(Summary(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                executive_summary=f"A {sample['duration']//60}-minute {sample['type'].replace('_', ' ')} conversation with clear outcomes and next steps identified.",
                detailed_summary=f"The conversation covered key business topics with actionable insights extracted. Customer engaged positively with the discussion.",
                key_topics=["Enterprise Solutions", "Pricing", "Integration", "Timeline"],
                decisions=["Follow-up scheduled", "Proposal to be sent"],
                important_moments=[{"timestamp": 120.0, "description": "Customer expressed strong interest"}, {"timestamp": 480.0, "description": "Next steps agreed"}],
                open_questions=["HIPAA compliance requirements?", "Specific integration needs?"],
                next_steps=["Send proposal", "Schedule demo", "Follow up next week"],
            ))

            # Sentiment
            db.add(SentimentResult(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                overall_sentiment=sample["overall_sentiment"],
                overall_score=0.7 if sample["overall_sentiment"] == "positive" else -0.4 if sample["overall_sentiment"] == "negative" else 0.1,
                customer_sentiment=sample["overall_sentiment"],
                agent_sentiment="positive",
                sentiment_trend="Neutral → Interested → Positive" if sample["overall_sentiment"] == "positive" else "Neutral → Frustrated → Negative",
                timeline=[
                    {"timestamp": 0, "speaker": "Customer", "sentiment": "neutral", "score": 0.0},
                    {"timestamp": 180, "speaker": "Customer", "sentiment": "interested", "score": 0.5},
                    {"timestamp": 420, "speaker": "Customer", "sentiment": sample["overall_sentiment"], "score": 0.8 if sample["overall_sentiment"] == "positive" else -0.6},
                ],
                frustration_detected=sample["overall_sentiment"] == "negative",
                satisfaction_detected=sample["overall_sentiment"] == "positive",
            ))

            # Intent
            db.add(IntentResult(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                primary_intent="purchase_intent" if sample["lead_score"] and sample["lead_score"] > 70 else "information_request",
                secondary_intents=["pricing_inquiry", "demo_request"],
                confidence=0.88,
                evidence=[{"text": "We are ready to move forward", "timestamp": 480.0}],
            ))

            # Sales Insight (only for sales-type conversations)
            if sample["lead_score"] is not None:
                db.add(SalesInsight(
                    id=str(uuid.uuid4()),
                    conversation_id=conv_id,
                    lead_score=sample["lead_score"],
                    purchase_intent=sample["purchase_intent"],
                    deal_health=sample["deal_health"],
                    budget_discussed=True,
                    budget_range="$5,000-$10,000/month",
                    decision_maker_present=True,
                    timeline_discussed=True,
                    timeline="Q3 this year",
                    buying_signals=[{"signal": "Customer confirmed budget authority", "timestamp": 200.0, "evidence": "I have full budget authority for this"}],
                    upsell_opportunities=["AI IVR", "WhatsApp integration"],
                    cross_sell_opportunities=["Contact Centre solution"],
                    stage="demo" if sample["lead_score"] > 70 else "qualified",
                    closing_probability=sample["lead_score"] / 100 * 0.9,
                ))

            # Action Items
            for j, (desc, owner, priority, status_val) in enumerate([
                ("Send pricing proposal", "Sales Representative", "high", "pending"),
                ("Schedule technical demo", "Sales Representative", "urgent", "completed" if i % 2 == 0 else "pending"),
                ("Share compliance documentation", "Sales Representative", "medium", "pending"),
                ("Review API integration requirements", "Customer", "medium", "pending"),
            ]):
                db.add(ActionItem(
                    id=str(uuid.uuid4()),
                    conversation_id=conv_id,
                    organization_id=demo_org.id,
                    description=desc,
                    owner=owner,
                    due_date="Friday" if j == 0 else "Next week",
                    priority=priority,
                    status=status_val,
                    source_timestamp=float(j * 120 + 60),
                    related_topic="Pricing" if j == 0 else "Sales",
                    created_at=created_at,
                ))

            # Objections
            if sample["type"] in ("sales", "product_demo", "follow_up"):
                for obj_cat, obj_desc, severity in [
                    ("security", "Customer concerned about data security compliance", "medium"),
                    ("pricing", "Customer found pricing higher than budget initially expected", "high"),
                ]:
                    db.add(Objection(
                        id=str(uuid.uuid4()),
                        conversation_id=conv_id,
                        category=obj_cat,
                        description=obj_desc,
                        exact_quote="We need to be sure about data security" if obj_cat == "security" else "The pricing seems a bit high",
                        timestamp=300.0 if obj_cat == "security" else 400.0,
                        severity=severity,
                        was_resolved=True,
                        suggested_response="Share SOC 2 documentation" if obj_cat == "security" else "Explain ROI and value proposition",
                    ))

            # Entities
            for entity_type, value, context in [
                ("competitor", "RingCentral", "Customer evaluating RingCentral"),
                ("product", "Salesforce", "Customer requires CRM integration"),
                ("company", "Demo Customer Corp", "Customer organization"),
            ]:
                db.add(Entity(
                    id=str(uuid.uuid4()),
                    conversation_id=conv_id,
                    entity_type=entity_type,
                    value=value,
                    context=context,
                    timestamp=100.0,
                    mention_count=2,
                ))

            # Pain Points
            db.add(PainPoint(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                category="financial",
                description="High costs from legacy system with no analytics",
                severity="high",
                desired_outcome="Cost reduction with intelligence capabilities",
                potential_solution="Cloud PBX with AI analytics",
                evidence="We're paying too much for what we get",
                timestamp=150.0,
            ))

            # Meeting Minutes
            db.add(MeetingMinutes(
                id=str(uuid.uuid4()),
                conversation_id=conv_id,
                objective="Sales discovery and platform presentation",
                participants_summary="Sales Representative, Customer Decision Maker",
                discussion_points=["Current system challenges", "Platform capabilities", "Pricing", "Security", "Implementation"],
                decisions=["Demo scheduled", "Proposal to be sent"],
                action_items_summary=["Send pricing proposal — Sales Rep", "Schedule demo — Sales Rep"],
                open_questions=["HIPAA requirements?", "Number of users?"],
                risks=["Competitor evaluation underway"],
                next_steps=["Send proposal by Friday", "Demo next week"],
                next_meeting="Technical Demo",
            ))

            # Recommendations
            for rec_cat, rec_action, rec_priority in [
                ("demo", "Schedule technical demo showing Salesforce integration", "urgent"),
                ("proposal", "Send enterprise pricing proposal within 24 hours", "high"),
                ("competitive", "Prepare competitive analysis vs RingCentral", "medium"),
            ]:
                db.add(Recommendation(
                    id=str(uuid.uuid4()),
                    conversation_id=conv_id,
                    category=rec_cat,
                    action=rec_action,
                    reasoning="Based on conversation analysis and customer signals",
                    priority=rec_priority,
                    urgency="today" if rec_priority == "urgent" else "this_week",
                    evidence=["Customer expressed strong interest", "Demo explicitly requested"],
                ))

            # Agent Score (only for applicable conversation types)
            if sample["agent_score"] is not None:
                db.add(AgentScore(
                    id=str(uuid.uuid4()),
                    conversation_id=conv_id,
                    overall_score=sample["agent_score"],
                    greeting_score=sample["agent_score"] + 5,
                    professionalism_score=sample["agent_score"] + 2,
                    empathy_score=sample["agent_score"] - 3,
                    listening_score=sample["agent_score"] - 5,
                    question_quality_score=sample["agent_score"] - 8,
                    product_knowledge_score=sample["agent_score"] + 6,
                    objection_handling_score=sample["agent_score"] - 10,
                    closing_score=sample["agent_score"] - 2,
                    talk_ratio=0.52,
                    interruption_count=2,
                    filler_word_count=8,
                    strengths=["Strong product knowledge", "Professional tone", "Clear communication"],
                    weaknesses=["Could ask more discovery questions", "Objection handling needs work"],
                    improvement_suggestions=["Use SPIN selling framework", "Practice active listening"],
                    coaching_notes="Good overall performance. Focus on discovery phase improvement.",
                    disclaimer="This is an AI-generated assessment. Review alongside direct observation.",
                ))

            # CRM Record (proposals only)
            if sample["lead_score"] and sample["lead_score"] > 60:
                db.add(CRMRecord(
                    id=str(uuid.uuid4()),
                    conversation_id=conv_id,
                    organization_id=demo_org.id,
                    crm_entity_type="lead",
                    proposed_changes={
                        "lead_stage": {"from": "contacted", "to": "qualified"},
                        "purchase_intent": {"from": "unknown", "to": sample["purchase_intent"]},
                        "lead_score": {"from": None, "to": sample["lead_score"]},
                        "notes": "AI-generated update from conversation analysis",
                    },
                    status="pending",
                ))

            # Transcript segments (add a few demo segments)
            for seg_idx, (start, end, speaker_label, text) in enumerate([
                (0.0, 8.0, "Sales Representative", "Good morning! This is James from TalkWiseAI. How are you today?"),
                (8.5, 18.0, "Customer", "Hi James, I'm doing well. We're actually evaluating communication platforms right now."),
                (18.5, 45.0, "Sales Representative", "That's great timing! Can you tell me a bit about your current setup and what's driving the evaluation?"),
                (45.5, 75.0, "Customer", "Sure. We're on an old PBX system, paying about six thousand a month, and we have zero visibility into our calls."),
                (75.5, 110.0, "Sales Representative", "I completely understand. That's a very common pain point. Our platform transforms call recordings into actionable intelligence automatically."),
            ]):
                db.add(TranscriptSegment(
                    id=str(uuid.uuid4()),
                    conversation_id=conv_id,
                    speaker_label=speaker_label,
                    start_time=start,
                    end_time=end,
                    text=text,
                    confidence=0.96,
                    sequence_index=seg_idx,
                ))

        # ---- Notifications ----
        print("Creating sample notifications...")
        for notif_type, title, message in [
            ("processing_complete", "Analysis Complete", '"Enterprise Sales Call — Meridian Financial Group" has been analyzed. View insights now.'),
            ("high_intent", "High Intent Lead Detected", "BlueSky Logistics shows 88/100 lead score — follow up immediately."),
            ("processing_complete", "Analysis Complete", '"Product Demo — TechCorp Solutions" has been analyzed.'),
        ]:
            db.add(Notification(
                id=str(uuid.uuid4()),
                user_id=agent_user.id,
                type=notif_type,
                title=title,
                message=message,
                is_read=False,
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
    seed_database()
