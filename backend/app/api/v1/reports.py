"""
Reports API Router.

POST /api/v1/reports/generate   — Generate executive, sales, sentiment, or QA reports
GET  /api/v1/reports/export/{id} — Export generated report in CSV or Markdown/PDF format
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.report_agent import ExecutiveReportAgent
from app.ai.pipeline.graph import get_llm_provider
from app.core.dependencies import get_current_user, get_db
from app.db.models import Conversation, SalesInsight, Objection, AgentScore, SentimentResult

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


@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(
    payload: GenerateReportRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Synthesize organization-wide conversation metrics into executive reports."""
    # Gather aggregate analytics
    total_convs_res = await db.execute(
        select(func.count(Conversation.id)).where(Conversation.organization_id == current_user.organization_id)
    )
    total_convs = total_convs_res.scalar_one()

    high_intent_res = await db.execute(
        select(func.count(SalesInsight.id))
        .join(Conversation)
        .where(
            Conversation.organization_id == current_user.organization_id,
            SalesInsight.purchase_intent == "high",
        )
    )
    high_intent_count = high_intent_res.scalar_one()

    analytics_summary = {
        "organization_id": current_user.organization_id,
        "total_conversations": total_convs,
        "high_intent_count": high_intent_count,
        "time_period": payload.time_period,
    }

    llm = get_llm_provider()
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

    csv_lines = ["Conversation ID,Title,Type,Status,Duration(s),Created At"]
    for c in convs:
        csv_lines.append(f'"{c.id}","{c.title}","{c.conversation_type}","{c.status}",{c.duration_seconds or 0},"{c.created_at.isoformat()}"')

    csv_content = "\n".join(csv_lines)
    return Response(
        content=csv_content,
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="talkwise_conversations_report.csv"'},
    )
