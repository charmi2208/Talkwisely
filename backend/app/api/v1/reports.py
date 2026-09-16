"""
Reports API Router.

POST /api/v1/reports/generate   — Generate executive, sales, sentiment, or QA reports
GET  /api/v1/reports/export/{id} — Export generated report in CSV or Markdown/PDF format
"""

import csv
import io
from datetime import datetime, timedelta
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.report_agent import ExecutiveReportAgent
from app.ai.pipeline.graph import llm_session
from app.core.dependencies import get_current_user, get_db
from app.db.models import ActionItem, AgentScore, Conversation, Objection, SalesInsight, SentimentResult

router = APIRouter(prefix="/reports", tags=["Reports & Analytics Exports"])


class GenerateReportRequest(BaseModel):
    report_type: str = "executive"  # executive | sales | sentiment_objections | team_qa
    time_period: str = "weekly"     # daily | weekly | monthly | custom


class GenerateReportResponse(BaseModel):
    title: str
    report_type: str
    time_period: str
    executive_summary: str
    key_insights: list[str]
    trends: list[dict]
    risks_and_bottlenecks: list[str]
    strategic_recommendations: list[str]
    formatted_markdown: str


PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30}


async def _collect_metrics(db: AsyncSession, org_id: str, time_period: str) -> dict:
    """Aggregate the numbers a report may cite, limited to the requested period."""
    since = datetime.utcnow() - timedelta(days=PERIOD_DAYS.get(time_period, 7))
    in_scope = (Conversation.organization_id == org_id, Conversation.created_at >= since)

    async def grouped(column, model):
        rows = await db.execute(
            select(column, func.count()).select_from(model).join(Conversation, model.conversation_id == Conversation.id)
            .where(*in_scope, column.is_not(None)).group_by(column)
        )
        return {k: v for k, v in rows.all()}

    by_type = await db.execute(
        select(Conversation.conversation_type, func.count()).where(*in_scope).group_by(Conversation.conversation_type)
    )
    conversations_by_type = {k: v for k, v in by_type.all()}
    avg_lead = await db.execute(
        select(func.avg(SalesInsight.lead_score)).join(Conversation, SalesInsight.conversation_id == Conversation.id)
        .where(*in_scope)
    )
    avg_agent = await db.execute(
        select(func.avg(AgentScore.overall_score)).join(Conversation, AgentScore.conversation_id == Conversation.id)
        .where(*in_scope)
    )
    objections = await db.execute(
        select(Objection.category, func.count().label("n")).join(Conversation, Objection.conversation_id == Conversation.id)
        .where(*in_scope).group_by(Objection.category).order_by(func.count().desc()).limit(5)
    )
    open_items = await db.execute(
        select(func.count()).select_from(ActionItem).join(Conversation, ActionItem.conversation_id == Conversation.id)
        .where(*in_scope, ActionItem.status.in_(("pending", "in_progress", "overdue")))
    )
    intents = await grouped(SalesInsight.purchase_intent, SalesInsight)
    lead_avg = avg_lead.scalar_one()
    agent_avg = avg_agent.scalar_one()

    return {
        "period": time_period,
        "period_start": since.date().isoformat(),
        "total_conversations": sum(conversations_by_type.values()),
        "conversations_by_type": conversations_by_type,
        "sentiment_distribution": await grouped(SentimentResult.overall_sentiment, SentimentResult),
        "purchase_intent_distribution": intents,
        "high_intent_count": intents.get("high", 0),
        "deal_health_distribution": await grouped(SalesInsight.deal_health, SalesInsight),
        "avg_lead_score": round(float(lead_avg), 1) if lead_avg is not None else None,
        "avg_agent_score": round(float(agent_avg), 1) if agent_avg is not None else None,
        "top_objections": [{"category": c, "count": n} for c, n in objections.all()],
        "open_action_items": open_items.scalar_one(),
    }


@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(
    payload: GenerateReportRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Synthesize organization-wide conversation metrics into executive reports."""
    analytics_summary = await _collect_metrics(db, current_user.organization_id, payload.time_period)

    async with llm_session() as llm:
        agent = ExecutiveReportAgent(llm)

        result = await agent.generate_report(
            report_type=payload.report_type,
            time_period=payload.time_period,
            analytics_summary=analytics_summary,
        )

    return GenerateReportResponse(**result)


@router.get("/export/csv")
async def export_conversations_csv(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export conversation metrics as CSV."""
    query = (
        select(Conversation)
        .where(Conversation.organization_id == current_user.organization_id)
        .order_by(Conversation.created_at.desc())
    )
    res = await db.execute(query)
    convs = res.scalars().all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Conversation ID", "Title", "Type", "Status", "Duration(s)", "Created At"])
    for c in convs:
        writer.writerow([c.id, c.title, c.conversation_type, c.status, c.duration_seconds or 0, c.created_at.isoformat()])
    csv_content = buffer.getvalue()
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="talkwise_conversations_report.csv"'},
    )
