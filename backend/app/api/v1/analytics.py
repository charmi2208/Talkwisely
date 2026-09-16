"""
Analytics API Routes.

GET /api/v1/analytics/overview        — Dashboard KPI metrics
GET /api/v1/analytics/conversations   — Conversation volume trends
GET /api/v1/analytics/sentiment       — Sentiment trends
GET /api/v1/analytics/sales           — Sales metrics
GET /api/v1/analytics/objections      — Objection analysis
GET /api/v1/analytics/agents          — Agent performance overview
GET /api/v1/analytics/topics          — Topic frequency
"""

from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.db.models import (
    ActionItem, AgentScore, Conversation, Entity, Objection, SalesInsight, SentimentResult
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])


def _default_date_range(days: int = 30) -> tuple[datetime, datetime]:
    now = datetime.utcnow()
    return now - timedelta(days=days), now


@router.get("/overview")
async def get_dashboard_overview(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return key dashboard metrics for the current organization."""
    org_id = current_user.organization_id
    date_from, date_to = _default_date_range(days)

    # Total conversations
    total_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
        )
    )
    total_conversations = total_result.scalar_one() or 0

    # By type
    type_result = await db.execute(
        select(Conversation.conversation_type, func.count(Conversation.id)).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
        ).group_by(Conversation.conversation_type)
    )
    by_type = {row[0]: row[1] for row in type_result}

    # High intent leads
    high_intent_result = await db.execute(
        select(func.count(SalesInsight.id)).join(
            Conversation, SalesInsight.conversation_id == Conversation.id
        ).where(
            Conversation.organization_id == org_id,
            SalesInsight.purchase_intent == "high",
            Conversation.created_at >= date_from,
        )
    )
    high_intent_leads = high_intent_result.scalar_one() or 0

    # Open action items
    open_actions_result = await db.execute(
        select(func.count(ActionItem.id)).where(
            ActionItem.organization_id == org_id,
            ActionItem.status == "pending",
        )
    )
    open_action_items = open_actions_result.scalar_one() or 0

    # Average lead score
    avg_score_result = await db.execute(
        select(func.avg(SalesInsight.lead_score)).join(
            Conversation, SalesInsight.conversation_id == Conversation.id
        ).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
            SalesInsight.lead_score.is_not(None),
        )
    )
    avg_lead_score = round(avg_score_result.scalar_one() or 0, 1)

    # Sentiment distribution
    sentiment_result = await db.execute(
        select(SentimentResult.overall_sentiment, func.count(SentimentResult.id)).join(
            Conversation, SentimentResult.conversation_id == Conversation.id
        ).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
        ).group_by(SentimentResult.overall_sentiment)
    )
    sentiment_dist = {row[0]: row[1] for row in sentiment_result}

    # Average agent score
    agent_score_result = await db.execute(
        select(func.avg(AgentScore.overall_score)).join(
            Conversation, AgentScore.conversation_id == Conversation.id
        ).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
        )
    )
    avg_agent_score = round(agent_score_result.scalar_one() or 0, 1)

    # Top objection category
    top_objection_result = await db.execute(
        select(Objection.category, func.count(Objection.id)).join(
            Conversation, Objection.conversation_id == Conversation.id
        ).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
        ).group_by(Objection.category).order_by(func.count(Objection.id).desc()).limit(1)
    )
    top_objection_row = top_objection_result.first()
    top_objection = top_objection_row[0] if top_objection_row else "none"

    # Completed conversations
    completed_result = await db.execute(
        select(func.count(Conversation.id)).where(
            Conversation.organization_id == org_id,
            Conversation.status == "completed",
            Conversation.created_at >= date_from,
        )
    )
    completed = completed_result.scalar_one() or 0

    # Overall dominant sentiment
    dominant_sentiment = "positive"
    if sentiment_dist:
        dominant_sentiment = max(sentiment_dist, key=sentiment_dist.get)

    return {
        "period_days": days,
        "total_conversations": total_conversations,
        "completed_conversations": completed,
        "conversations_by_type": by_type,
        "high_intent_leads": high_intent_leads,
        "open_action_items": open_action_items,
        "average_lead_score": avg_lead_score,
        "average_agent_score": avg_agent_score,
        "sentiment_distribution": sentiment_dist,
        "dominant_sentiment": dominant_sentiment,
        "top_objection_category": top_objection,
    }


@router.get("/conversations")
async def get_conversation_trends(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return daily conversation volume for the trend chart."""
    org_id = current_user.organization_id
    date_from = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Conversation.created_at).label("date"),
            func.count(Conversation.id).label("count"),
        ).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
        ).group_by(func.date(Conversation.created_at))
        .order_by(func.date(Conversation.created_at))
    )
    rows = result.all()

    return {
        "data": [{"date": str(r.date), "count": r.count} for r in rows],
        "period_days": days,
    }


@router.get("/sentiment")
async def get_sentiment_trends(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return sentiment breakdown over time."""
    org_id = current_user.organization_id
    date_from = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.date(Conversation.created_at).label("date"),
            SentimentResult.overall_sentiment.label("sentiment"),
            func.count(SentimentResult.id).label("count"),
        ).join(
            Conversation, SentimentResult.conversation_id == Conversation.id
        ).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
        ).group_by(func.date(Conversation.created_at), SentimentResult.overall_sentiment)
        .order_by(func.date(Conversation.created_at))
    )
    rows = result.all()

    return {
        "data": [{"date": str(r.date), "sentiment": r.sentiment, "count": r.count} for r in rows],
        "period_days": days,
    }


@router.get("/objections")
async def get_objection_analysis(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return objection category breakdown."""
    org_id = current_user.organization_id
    date_from = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            Objection.category,
            func.count(Objection.id).label("count"),
            func.avg(
                case(
                    (Objection.severity == "high", 3),
                    (Objection.severity == "medium", 2),
                    else_=1,
                )
            ).label("avg_severity"),
        ).join(
            Conversation, Objection.conversation_id == Conversation.id
        ).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
        ).group_by(Objection.category)
        .order_by(func.count(Objection.id).desc())
    )
    rows = result.all()

    return {
        "data": [
            {"category": r.category, "count": r.count, "avg_severity": round(float(r.avg_severity or 1), 2)}
            for r in rows
        ],
        "period_days": days,
    }


@router.get("/sales")
async def get_sales_metrics(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return sales pipeline and lead score metrics."""
    org_id = current_user.organization_id
    date_from = datetime.utcnow() - timedelta(days=days)

    # Intent distribution
    intent_result = await db.execute(
        select(SalesInsight.purchase_intent, func.count(SalesInsight.id)).join(
            Conversation, SalesInsight.conversation_id == Conversation.id
        ).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
            SalesInsight.purchase_intent.is_not(None),
        ).group_by(SalesInsight.purchase_intent)
    )
    intent_dist = {row[0]: row[1] for row in intent_result}

    # Stage distribution
    stage_result = await db.execute(
        select(SalesInsight.stage, func.count(SalesInsight.id)).join(
            Conversation, SalesInsight.conversation_id == Conversation.id
        ).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
            SalesInsight.stage.is_not(None),
        ).group_by(SalesInsight.stage)
    )
    stage_dist = {row[0]: row[1] for row in stage_result}

    # Top competitors
    competitor_result = await db.execute(
        select(Entity.value, func.count(Entity.id).label("mentions")).join(
            Conversation, Entity.conversation_id == Conversation.id
        ).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
            Entity.entity_type == "competitor",
        ).group_by(Entity.value)
        .order_by(func.count(Entity.id).desc())
        .limit(5)
    )
    top_competitors = [{"name": r.value, "mentions": r.mentions} for r in competitor_result]

    return {
        "purchase_intent_distribution": intent_dist,
        "pipeline_stage_distribution": stage_dist,
        "top_competitors": top_competitors,
        "period_days": days,
    }


@router.get("/agents")
async def get_agent_performance(
    days: int = Query(30, ge=1, le=365),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return agent performance summary."""
    org_id = current_user.organization_id
    date_from = datetime.utcnow() - timedelta(days=days)

    result = await db.execute(
        select(
            func.avg(AgentScore.overall_score).label("avg_score"),
            func.avg(AgentScore.empathy_score).label("avg_empathy"),
            func.avg(AgentScore.product_knowledge_score).label("avg_product_knowledge"),
            func.avg(AgentScore.objection_handling_score).label("avg_objection_handling"),
            func.avg(AgentScore.closing_score).label("avg_closing"),
            func.count(AgentScore.id).label("total_scored"),
        ).join(
            Conversation, AgentScore.conversation_id == Conversation.id
        ).where(
            Conversation.organization_id == org_id,
            Conversation.created_at >= date_from,
        )
    )
    row = result.first()

    def _r(v):
        return round(float(v or 0), 1)

    return {
        "average_scores": {
            "overall": _r(row.avg_score),
            "empathy": _r(row.avg_empathy),
            "product_knowledge": _r(row.avg_product_knowledge),
            "objection_handling": _r(row.avg_objection_handling),
            "closing": _r(row.avg_closing),
        },
        "total_conversations_scored": row.total_scored or 0,
        "period_days": days,
    }
