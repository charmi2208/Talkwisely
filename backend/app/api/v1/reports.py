"""
Reports API Router.

POST /api/v1/reports/generate          — Generate and save a report (admin, manager)
GET  /api/v1/reports                   — Saved reports, newest first (admin, manager)
GET  /api/v1/reports/{id}              — One saved report
GET  /api/v1/reports/{id}/download     — Download as PDF, Markdown or CSV (?format=pdf|md|csv)
GET  /api/v1/reports/export/csv        — Export the conversations you can see as CSV

Report types: executive, conversation, sales, sentiment, objections, team_qa (agent
performance). Reports cite only metrics computed here; without an AI model they list
the metrics instead of inventing analysis.
"""

import csv
import io
import re
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.report_agent import REPORT_FOCUS, ExecutiveReportAgent
from app.ai.pipeline.graph import llm_session
from app.core.access import conversation_scope
from app.core.dependencies import get_current_user, get_db, require_roles
from app.db.models import (
    ActionItem, AgentScore, AuditLog, Conversation, Objection, Report, SalesInsight, SentimentResult, User,
)
from app.services.report_export import report_csv, report_pdf

router = APIRouter(prefix="/reports", tags=["Reports & Analytics Exports"])

PERIOD_DAYS = {"daily": 1, "weekly": 7, "monthly": 30, "quarterly": 90}


class GenerateReportRequest(BaseModel):
    report_type: str = "executive"
    time_period: str = "weekly"  # daily | weekly | monthly | quarterly


class GenerateReportResponse(BaseModel):
    id: Optional[str] = None
    title: str
    report_type: str
    time_period: str
    executive_summary: str
    key_insights: list[str]
    trends: list[dict]
    risks_and_bottlenecks: list[str]
    strategic_recommendations: list[str]
    formatted_markdown: str
    created_at: Optional[str] = None
    created_by_name: Optional[str] = None


class ReportListItem(BaseModel):
    id: str
    title: str
    report_type: str
    time_period: str
    date_from: Optional[str]
    date_to: Optional[str]
    created_at: str
    created_by_name: Optional[str] = None


async def _collect_metrics(db: AsyncSession, org_id: str, time_period: str) -> dict:
    """Aggregate the numbers a report may cite, limited to the requested period."""
    since = datetime.utcnow() - timedelta(days=PERIOD_DAYS.get(time_period, 7))
    in_scope = (Conversation.organization_id == org_id, Conversation.created_at >= since)

    async def grouped(column, model) -> dict:
        rows = await db.execute(
            select(column, func.count()).select_from(model).join(Conversation, model.conversation_id == Conversation.id)
            .where(*in_scope, column.is_not(None)).group_by(column)
        )
        return {k: v for k, v in rows.all()}

    async def scalar(stmt):
        return (await db.execute(stmt)).scalar_one()

    conversations_by_type = {k: v for k, v in (await db.execute(
        select(Conversation.conversation_type, func.count()).where(*in_scope).group_by(Conversation.conversation_type)
    )).all()}
    conversations_by_status = {k: v for k, v in (await db.execute(
        select(Conversation.status, func.count()).where(*in_scope).group_by(Conversation.status)
    )).all()}
    lead_avg = await scalar(
        select(func.avg(SalesInsight.lead_score)).join(Conversation, SalesInsight.conversation_id == Conversation.id).where(*in_scope)
    )
    agent_avg = await scalar(
        select(func.avg(AgentScore.overall_score)).join(Conversation, AgentScore.conversation_id == Conversation.id).where(*in_scope)
    )
    duration_avg = await scalar(
        select(func.avg(Conversation.duration_seconds)).where(*in_scope, Conversation.duration_seconds.is_not(None))
    )
    objections = (await db.execute(
        select(
            Objection.category,
            func.count().label("n"),
            func.sum(case((Objection.was_resolved.is_(True), 1), else_=0)).label("resolved"),
        )
        .join(Conversation, Objection.conversation_id == Conversation.id)
        .where(*in_scope).group_by(Objection.category).order_by(func.count().desc()).limit(8)
    )).all()
    agent_scores = (await db.execute(
        select(User.full_name, func.avg(AgentScore.overall_score), func.count(AgentScore.id))
        .join(Conversation, AgentScore.conversation_id == Conversation.id)
        .join(User, Conversation.created_by == User.id)
        .where(*in_scope).group_by(User.full_name).order_by(func.avg(AgentScore.overall_score).desc())
    )).all()
    open_items = await scalar(
        select(func.count()).select_from(ActionItem)
        .where(ActionItem.organization_id == org_id, ActionItem.status.in_(("pending", "in_progress", "overdue")))
    )
    intents = await grouped(SalesInsight.purchase_intent, SalesInsight)

    return {
        "period": time_period,
        "period_start": since.date().isoformat(),
        "total_conversations": sum(conversations_by_type.values()),
        "conversations_by_type": conversations_by_type,
        "conversations_by_status": conversations_by_status,
        "avg_duration_seconds": round(float(duration_avg)) if duration_avg is not None else None,
        "sentiment_distribution": await grouped(SentimentResult.overall_sentiment, SentimentResult),
        "purchase_intent_distribution": intents,
        "high_intent_count": intents.get("high", 0),
        "deal_health_distribution": await grouped(SalesInsight.deal_health, SalesInsight),
        "avg_lead_score": round(float(lead_avg), 1) if lead_avg is not None else None,
        "avg_agent_score": round(float(agent_avg), 1) if agent_avg is not None else None,
        "agent_scores": [
            {"name": name, "avg_score": round(float(avg), 1), "scored": n} for name, avg, n in agent_scores if avg is not None
        ],
        "top_objections": [{"category": c, "count": n, "resolved": int(r or 0)} for c, n, r in objections],
        "open_action_items": open_items,
    }


def _report_payload(report: Report, created_by_name: Optional[str] = None) -> GenerateReportResponse:
    data = report.data or {}
    return GenerateReportResponse(
        id=report.id,
        title=report.title,
        report_type=report.report_type,
        time_period=data.get("time_period", ""),
        executive_summary=data.get("executive_summary", ""),
        key_insights=data.get("key_insights", []),
        trends=data.get("trends", []),
        risks_and_bottlenecks=data.get("risks_and_bottlenecks", []),
        strategic_recommendations=data.get("strategic_recommendations", []),
        formatted_markdown=data.get("formatted_markdown", ""),
        created_at=report.created_at.isoformat(),
        created_by_name=created_by_name,
    )


async def _get_report(db: AsyncSession, report_id: str, organization_id: str) -> tuple[Report, Optional[str]]:
    row = (await db.execute(
        select(Report, User.full_name)
        .join(User, Report.created_by == User.id, isouter=True)
        .where(Report.id == report_id, Report.organization_id == organization_id)
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Report not found")
    return row[0], row[1]


@router.post("/generate", response_model=GenerateReportResponse)
async def generate_report(
    payload: GenerateReportRequest,
    current_user=Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Generate a report from this organization's metrics and save it."""
    if payload.report_type not in REPORT_FOCUS:
        raise HTTPException(status_code=422, detail=f"report_type must be one of: {', '.join(REPORT_FOCUS)}")
    if payload.time_period not in PERIOD_DAYS:
        raise HTTPException(status_code=422, detail=f"time_period must be one of: {', '.join(PERIOD_DAYS)}")

    metrics = await _collect_metrics(db, current_user.organization_id, payload.time_period)
    async with llm_session() as llm:
        result = await ExecutiveReportAgent(llm).generate_report(
            report_type=payload.report_type,
            time_period=payload.time_period,
            analytics_summary=metrics,
        )

    now = datetime.utcnow()
    report = Report(
        organization_id=current_user.organization_id,
        created_by=current_user.id,
        report_type=payload.report_type,
        title=result["title"],
        date_from=now - timedelta(days=PERIOD_DAYS[payload.time_period]),
        date_to=now,
        data={**result, "metrics": metrics},
        status="completed",
    )
    db.add(report)
    await db.flush()
    db.add(AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="report_generate",
        resource_type="report",
        resource_id=report.id,
        details={"report_type": payload.report_type, "time_period": payload.time_period},
    ))
    await db.commit()
    return _report_payload(report, current_user.full_name)


@router.get("", response_model=list[ReportListItem])
async def list_reports(
    limit: int = Query(25, ge=1, le=100),
    current_user=Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Reports saved for this organization, newest first."""
    rows = (await db.execute(
        select(Report, User.full_name)
        .join(User, Report.created_by == User.id, isouter=True)
        .where(Report.organization_id == current_user.organization_id)
        .order_by(Report.created_at.desc())
        .limit(limit)
    )).all()
    return [
        ReportListItem(
            id=r.id,
            title=r.title,
            report_type=r.report_type,
            time_period=(r.data or {}).get("time_period", ""),
            date_from=r.date_from.isoformat() if r.date_from else None,
            date_to=r.date_to.isoformat() if r.date_to else None,
            created_at=r.created_at.isoformat(),
            created_by_name=name,
        )
        for r, name in rows
    ]


@router.get("/export/csv")
async def export_conversations_csv(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Export the conversations you can see, with key AI metrics, as CSV."""
    rows = (await db.execute(
        select(Conversation, SalesInsight.lead_score, SalesInsight.purchase_intent, SentimentResult.overall_sentiment)
        .outerjoin(SalesInsight, SalesInsight.conversation_id == Conversation.id)
        .outerjoin(SentimentResult, SentimentResult.conversation_id == Conversation.id)
        .where(*conversation_scope(current_user))
        .order_by(Conversation.created_at.desc())
    )).all()

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow([
        "Conversation ID", "Title", "Type", "Status", "Duration (s)",
        "Lead score", "Purchase intent", "Sentiment", "Created at (UTC)",
    ])
    for c, lead_score, intent, sentiment in rows:
        writer.writerow([
            c.id, c.title, c.conversation_type, c.status, c.duration_seconds or "",
            lead_score if lead_score is not None else "", intent or "", sentiment or "", c.created_at.isoformat(),
        ])
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": 'attachment; filename="talkwise_conversations.csv"'},
    )


@router.get("/{report_id}", response_model=GenerateReportResponse)
async def get_report(
    report_id: str,
    current_user=Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """One saved report."""
    report, name = await _get_report(db, report_id, current_user.organization_id)
    return _report_payload(report, name)


@router.get("/{report_id}/download")
async def download_report(
    report_id: str,
    format: str = Query("pdf", pattern="^(pdf|md|csv)$"),
    current_user=Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Download a saved report as PDF, Markdown or CSV."""
    report, _ = await _get_report(db, report_id, current_user.organization_id)
    data = report.data or {}
    slug = re.sub(r"[^a-z0-9]+", "-", report.title.lower()).strip("-") or "report"
    filename = f"{slug}-{report.created_at:%Y%m%d}"

    if format == "pdf":
        content: bytes | str = report_pdf(report.title, data.get("formatted_markdown", ""), report.created_at)
        media_type = "application/pdf"
    elif format == "md":
        content = data.get("formatted_markdown", "")
        media_type = "text/markdown"
    else:
        content = report_csv(report.title, data.get("metrics", {}), {
            "Key insights": data.get("key_insights", []),
            "Risks": data.get("risks_and_bottlenecks", []),
            "Recommendations": data.get("strategic_recommendations", []),
        })
        media_type = "text/csv"
    return Response(
        content=content,
        media_type=media_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}.{format}"'},
    )
