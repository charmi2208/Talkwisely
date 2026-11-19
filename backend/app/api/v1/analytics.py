"""
Analytics API Routes.

Every endpoint accepts the same filters:
  days               look-back window (1-365, default 30)
  conversation_type  e.g. sales, customer_support, internal_meeting
  agent_id           only conversations uploaded by this user (admins/managers)

Agents always get their own conversations only (see app/core/access.py).

GET /api/v1/analytics/overview        — KPI metrics with change vs the previous period
GET /api/v1/analytics/conversations   — Daily volume, split into calls and meetings
GET /api/v1/analytics/sentiment       — Daily sentiment counts and average score
GET /api/v1/analytics/objections      — Objection categories, severity, resolution rate
GET /api/v1/analytics/sales           — Purchase intent, pipeline stages, competitors
GET /api/v1/analytics/agents          — Average QA scores and a per-person leaderboard
GET /api/v1/analytics/topics          — Most frequent key topics
"""

from collections import Counter
from datetime import date, datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.action_items import visible_action_items
from app.core.access import conversation_scope, is_privileged
from app.core.dependencies import get_current_user, get_db
from app.db.models import (
    ActionItem, AgentScore, Conversation, Entity, Objection, SalesInsight, SentimentResult, Summary, User,
)

router = APIRouter(prefix="/analytics", tags=["Analytics"])

# Conversation types counted as meetings; everything else is a call
MEETING_TYPES = ("internal_meeting", "client_meeting", "meeting")
IN_PROGRESS_STATUSES = ("uploaded", "queued", "processing", "transcribing", "analyzing")


class AnalyticsFilters:
    """Shared query parameters, resolved into SQL conditions on Conversation."""

    def __init__(
        self,
        days: int = Query(30, ge=1, le=365),
        conversation_type: Optional[str] = Query(None),
        agent_id: Optional[str] = Query(None),
    ):
        self.days = days
        self.conversation_type = conversation_type
        self.agent_id = agent_id

    def conditions(self, user, offset_periods: int = 0) -> list:
        """Conditions for the current window, or an earlier window of the same length."""
        now = datetime.utcnow()
        end = now - timedelta(days=self.days * offset_periods)
        start = end - timedelta(days=self.days)
        conds = conversation_scope(user) + [Conversation.created_at >= start, Conversation.created_at < end]
        if self.conversation_type:
            conds.append(Conversation.conversation_type == self.conversation_type)
        if self.agent_id and is_privileged(user):
            conds.append(Conversation.created_by == self.agent_id)
        return conds


def _pct_change(current: float, previous: float) -> float | None:
    """Percent change vs the previous period; None when there's nothing to compare with."""
    if not previous:
        return None
    return round((current - previous) / previous * 100, 1)


def _round(value, digits: int = 1) -> float | None:
    return round(float(value), digits) if value is not None else None


async def _scalar(db: AsyncSession, stmt):
    return (await db.execute(stmt)).scalar_one()


async def _period_metrics(db: AsyncSession, conds: list) -> dict:
    """Headline numbers for one window."""
    total = await _scalar(db, select(func.count(Conversation.id)).where(*conds))
    high_intent = await _scalar(
        db,
        select(func.count(SalesInsight.id))
        .join(Conversation, SalesInsight.conversation_id == Conversation.id)
        .where(*conds, SalesInsight.purchase_intent == "high"),
    )
    avg_agent = await _scalar(
        db,
        select(func.avg(AgentScore.overall_score))
        .join(Conversation, AgentScore.conversation_id == Conversation.id)
        .where(*conds),
    )
    avg_sentiment = await _scalar(
        db,
        select(func.avg(SentimentResult.overall_score))
        .join(Conversation, SentimentResult.conversation_id == Conversation.id)
        .where(*conds),
    )
    return {
        "total": total or 0,
        "high_intent": high_intent or 0,
        "avg_agent": _round(avg_agent),
        "avg_sentiment": _round(avg_sentiment, 2),
    }


@router.get("/overview")
async def get_dashboard_overview(
    filters: AnalyticsFilters = Depends(),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Key dashboard metrics, with change against the previous window of the same length."""
    conds = filters.conditions(current_user)
    current = await _period_metrics(db, conds)
    previous = await _period_metrics(db, filters.conditions(current_user, offset_periods=1))

    by_type = {
        row[0]: row[1]
        for row in await db.execute(
            select(Conversation.conversation_type, func.count(Conversation.id))
            .where(*conds).group_by(Conversation.conversation_type)
        )
    }
    by_status = {
        row[0]: row[1]
        for row in await db.execute(
            select(Conversation.status, func.count(Conversation.id)).where(*conds).group_by(Conversation.status)
        )
    }
    meetings = sum(count for ctype, count in by_type.items() if ctype in MEETING_TYPES)

    # Open work is current state, not limited to the date window
    task_scope = visible_action_items(current_user)
    if filters.agent_id and is_privileged(current_user):
        task_scope.append(or_(Conversation.created_by == filters.agent_id, ActionItem.created_by == filters.agent_id))

    def count_tasks(*extra):
        return (
            select(func.count(ActionItem.id))
            .outerjoin(Conversation, ActionItem.conversation_id == Conversation.id)
            .where(*task_scope, *extra)
        )

    open_actions = await _scalar(db, count_tasks(ActionItem.status.in_(("pending", "in_progress", "overdue"))))
    overdue_actions = await _scalar(
        db, count_tasks(ActionItem.status != "completed", ActionItem.due_date_parsed < datetime.utcnow())
    )

    avg_lead = await _scalar(
        db,
        select(func.avg(SalesInsight.lead_score))
        .join(Conversation, SalesInsight.conversation_id == Conversation.id)
        .where(*conds, SalesInsight.lead_score.is_not(None)),
    )
    sales_opportunities = await _scalar(
        db,
        select(func.count(SalesInsight.id))
        .join(Conversation, SalesInsight.conversation_id == Conversation.id)
        .where(*conds, SalesInsight.stage.not_in(("won", "lost"))),
    )
    avg_closing = await _scalar(
        db,
        select(func.avg(SalesInsight.closing_probability))
        .join(Conversation, SalesInsight.conversation_id == Conversation.id)
        .where(*conds, SalesInsight.closing_probability.is_not(None)),
    )
    avg_duration = await _scalar(
        db, select(func.avg(Conversation.duration_seconds)).where(*conds, Conversation.duration_seconds.is_not(None))
    )

    sentiment_dist = {
        row[0]: row[1]
        for row in await db.execute(
            select(SentimentResult.overall_sentiment, func.count(SentimentResult.id))
            .join(Conversation, SentimentResult.conversation_id == Conversation.id)
            .where(*conds).group_by(SentimentResult.overall_sentiment)
        )
    }
    top_objection_row = (await db.execute(
        select(Objection.category, func.count(Objection.id))
        .join(Conversation, Objection.conversation_id == Conversation.id)
        .where(*conds).group_by(Objection.category)
        .order_by(func.count(Objection.id).desc()).limit(1)
    )).first()

    return {
        "period_days": filters.days,
        "total_conversations": current["total"],
        "total_calls": current["total"] - meetings,
        "total_meetings": meetings,
        "completed_conversations": by_status.get("completed", 0),
        "in_progress_conversations": sum(by_status.get(s, 0) for s in IN_PROGRESS_STATUSES),
        "failed_conversations": by_status.get("failed", 0),
        "conversations_by_type": by_type,
        "high_intent_leads": current["high_intent"],
        "sales_opportunities": sales_opportunities or 0,
        "average_closing_probability": _round(avg_closing, 2),
        "open_action_items": open_actions or 0,
        "overdue_action_items": overdue_actions or 0,
        "average_lead_score": _round(avg_lead) or 0,
        "average_agent_score": current["avg_agent"] or 0,
        "average_sentiment_score": current["avg_sentiment"],
        "average_duration_seconds": _round(avg_duration, 0),
        "sentiment_distribution": sentiment_dist,
        "dominant_sentiment": max(sentiment_dist, key=sentiment_dist.get) if sentiment_dist else None,
        "top_objection_category": top_objection_row[0] if top_objection_row else None,
        "changes": {
            "total_conversations_pct": _pct_change(current["total"], previous["total"]),
            "high_intent_leads_pct": _pct_change(current["high_intent"], previous["high_intent"]),
            "average_agent_score_points": (
                round(current["avg_agent"] - previous["avg_agent"], 1)
                if current["avg_agent"] is not None and previous["avg_agent"] is not None else None
            ),
            "average_sentiment_score_points": (
                round(current["avg_sentiment"] - previous["avg_sentiment"], 2)
                if current["avg_sentiment"] is not None and previous["avg_sentiment"] is not None else None
            ),
        },
    }


def _day_range(days: int) -> list[str]:
    today = date.today()
    return [(today - timedelta(days=offset)).isoformat() for offset in range(days - 1, -1, -1)]


@router.get("/conversations")
async def get_conversation_trends(
    filters: AnalyticsFilters = Depends(),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Daily conversation volume (every day in the window, zeros included)."""
    rows = (await db.execute(
        select(
            func.date(Conversation.created_at).label("day"),
            func.sum(case((Conversation.conversation_type.in_(MEETING_TYPES), 1), else_=0)).label("meetings"),
            func.count(Conversation.id).label("total"),
            func.avg(Conversation.duration_seconds).label("avg_duration"),
        )
        .where(*filters.conditions(current_user))
        .group_by(func.date(Conversation.created_at))
    )).all()
    by_day = {str(r.day): r for r in rows}

    data = []
    for day in _day_range(filters.days):
        r = by_day.get(day)
        total = int(r.total) if r else 0
        meetings = int(r.meetings or 0) if r else 0
        data.append({
            "date": day,
            "total": total,
            "calls": total - meetings,
            "meetings": meetings,
            "avg_duration_seconds": _round(r.avg_duration, 0) if r else None,
        })
    return {"data": data, "period_days": filters.days}


@router.get("/sentiment")
async def get_sentiment_trends(
    filters: AnalyticsFilters = Depends(),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Sentiment counts and average score per day."""
    rows = (await db.execute(
        select(
            func.date(Conversation.created_at).label("day"),
            SentimentResult.overall_sentiment.label("sentiment"),
            func.count(SentimentResult.id).label("count"),
            func.avg(SentimentResult.overall_score).label("avg_score"),
        )
        .join(Conversation, SentimentResult.conversation_id == Conversation.id)
        .where(*filters.conditions(current_user))
        .group_by(func.date(Conversation.created_at), SentimentResult.overall_sentiment)
    )).all()

    days: dict[str, dict] = {}
    for r in rows:
        entry = days.setdefault(str(r.day), {
            "date": str(r.day), "positive": 0, "neutral": 0, "negative": 0, "mixed": 0, "_score": 0.0, "_n": 0,
        })
        key = r.sentiment if r.sentiment in ("positive", "neutral", "negative", "mixed") else "neutral"
        entry[key] += r.count
        if r.avg_score is not None:
            entry["_score"] += float(r.avg_score) * r.count
            entry["_n"] += r.count

    data = []
    for day in sorted(days):
        entry = days[day]
        n = entry.pop("_n")
        score = entry.pop("_score")
        entry["average_score"] = round(score / n, 2) if n else None
        data.append(entry)
    return {"data": data, "period_days": filters.days}


@router.get("/objections")
async def get_objection_analysis(
    filters: AnalyticsFilters = Depends(),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Objection categories with frequency, average severity (1-3) and resolution rate."""
    rows = (await db.execute(
        select(
            Objection.category,
            func.count(Objection.id).label("count"),
            func.avg(case((Objection.severity == "high", 3), (Objection.severity == "medium", 2), else_=1)).label("avg_severity"),
            func.sum(case((Objection.was_resolved.is_(True), 1), else_=0)).label("resolved"),
        )
        .join(Conversation, Objection.conversation_id == Conversation.id)
        .where(*filters.conditions(current_user))
        .group_by(Objection.category)
        .order_by(func.count(Objection.id).desc())
    )).all()

    return {
        "data": [
            {
                "category": r.category,
                "count": r.count,
                "avg_severity": round(float(r.avg_severity or 1), 2),
                "resolved": int(r.resolved or 0),
                "resolution_rate": round(int(r.resolved or 0) / r.count, 2) if r.count else 0,
            }
            for r in rows
        ],
        "period_days": filters.days,
    }


@router.get("/sales")
async def get_sales_metrics(
    filters: AnalyticsFilters = Depends(),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Purchase intent, pipeline stage and deal health distributions plus top competitors."""
    conds = filters.conditions(current_user)

    async def distribution(column) -> dict:
        rows = await db.execute(
            select(column, func.count(SalesInsight.id))
            .join(Conversation, SalesInsight.conversation_id == Conversation.id)
            .where(*conds, column.is_not(None)).group_by(column)
        )
        return {row[0]: row[1] for row in rows}

    competitor_rows = await db.execute(
        select(Entity.value, func.count(Entity.id).label("mentions"))
        .join(Conversation, Entity.conversation_id == Conversation.id)
        .where(*conds, Entity.entity_type == "competitor")
        .group_by(Entity.value).order_by(func.count(Entity.id).desc()).limit(5)
    )

    return {
        "purchase_intent_distribution": await distribution(SalesInsight.purchase_intent),
        "pipeline_stage_distribution": await distribution(SalesInsight.stage),
        "deal_health_distribution": await distribution(SalesInsight.deal_health),
        "top_competitors": [{"name": r.value, "mentions": r.mentions} for r in competitor_rows],
        "period_days": filters.days,
    }


@router.get("/agents")
async def get_agent_performance(
    filters: AnalyticsFilters = Depends(),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Average AI QA scores overall and per person (agents see only themselves).

    Scores are AI-generated assessments, attributed to the user who uploaded the call.
    """
    conds = filters.conditions(current_user)
    score_columns = {
        "overall": AgentScore.overall_score,
        "empathy": AgentScore.empathy_score,
        "listening": AgentScore.listening_score,
        "product_knowledge": AgentScore.product_knowledge_score,
        "objection_handling": AgentScore.objection_handling_score,
        "closing": AgentScore.closing_score,
    }

    totals = (await db.execute(
        select(*[func.avg(col).label(name) for name, col in score_columns.items()],
               func.count(AgentScore.id).label("scored"))
        .join(Conversation, AgentScore.conversation_id == Conversation.id)
        .where(*conds)
    )).first()

    people = (await db.execute(
        select(
            User.id, User.full_name,
            func.count(AgentScore.id).label("scored"),
            *[func.avg(col).label(name) for name, col in score_columns.items()],
        )
        .join(Conversation, AgentScore.conversation_id == Conversation.id)
        .join(User, Conversation.created_by == User.id)
        .where(*conds)
        .group_by(User.id, User.full_name)
        .order_by(func.avg(AgentScore.overall_score).desc())
    )).all()

    return {
        "average_scores": {name: _round(getattr(totals, name)) or 0 for name in score_columns},
        "total_conversations_scored": totals.scored or 0,
        "leaderboard": [
            {
                "user_id": p.id,
                "name": p.full_name,
                "conversations_scored": p.scored,
                "scores": {name: _round(getattr(p, name)) for name in score_columns},
            }
            for p in people
        ],
        "period_days": filters.days,
        "disclaimer": "Scores are AI-generated assessments and should be used as one input among many.",
    }


@router.get("/topics")
async def get_topic_frequency(
    filters: AnalyticsFilters = Depends(),
    limit: int = Query(10, ge=1, le=50),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Most frequent key topics across conversation summaries."""
    rows = (await db.execute(
        select(Summary.key_topics)
        .join(Conversation, Summary.conversation_id == Conversation.id)
        .where(*filters.conditions(current_user))
    )).scalars().all()

    counter: Counter[str] = Counter()
    display: dict[str, str] = {}
    for topics in rows:
        for topic in topics or []:
            if not isinstance(topic, str) or not topic.strip():
                continue
            key = topic.strip().lower()
            counter[key] += 1
            display.setdefault(key, topic.strip())

    return {
        "data": [{"topic": display[key], "count": count} for key, count in counter.most_common(limit)],
        "period_days": filters.days,
    }
