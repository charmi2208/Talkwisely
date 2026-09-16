"""
Sales Pipeline & Objections API Router.

GET /api/v1/sales/pipeline   — Pipeline stage breakdown with lead scores & deal health
GET /api/v1/sales/objections — Objection matrix by category, frequency, and severity
"""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.db.models import Conversation, SalesInsight, Objection

router = APIRouter(prefix="/sales", tags=["Sales Intelligence"])


class SalesLeadItem(BaseModel):
    conversation_id: str
    title: str
    lead_score: Optional[int]
    purchase_intent: Optional[str]
    deal_health: Optional[str]
    pipeline_stage: Optional[str]
    budget_range: Optional[str]
    created_at: str


class ObjectionSummary(BaseModel):
    category: str
    count: int
    resolved_count: int
    unresolved_count: int


@router.get("/pipeline", response_model=list[SalesLeadItem])
async def get_sales_pipeline(
    stage: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch sales calls organized by pipeline stage, lead score, and deal health."""
    query = (
        select(Conversation, SalesInsight)
        .join(SalesInsight, Conversation.id == SalesInsight.conversation_id)
        .where(Conversation.organization_id == current_user.organization_id)
    )

    if stage:
        query = query.where(SalesInsight.stage == stage)
    if min_score is not None:
        query = query.where(SalesInsight.lead_score >= min_score)

    query = query.order_by(SalesInsight.lead_score.desc().nullslast())
    res = await db.execute(query)
    rows = res.all()

    items = []
    for conv, sales in rows:
        items.append(
            SalesLeadItem(
                conversation_id=conv.id,
                title=conv.title,
                lead_score=sales.lead_score,
                purchase_intent=sales.purchase_intent,
                deal_health=sales.deal_health,
                pipeline_stage=sales.stage,
                budget_range=sales.budget_range,
                created_at=conv.created_at.isoformat(),
            )
        )

    return items


@router.get("/objections", response_model=list[ObjectionSummary])
async def get_objection_matrix(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Fetch objection frequency and resolution metrics across all sales calls."""
    query = (
        select(
            Objection.category,
            func.count(Objection.id).label("total"),
            func.sum(func.cast(Objection.was_resolved, Integer if hasattr(Objection, 'was_resolved') else Integer)).label("resolved")
        )
        .join(Conversation, Objection.conversation_id == Conversation.id)
        .where(Conversation.organization_id == current_user.organization_id)
        .group_by(Objection.category)
    )

    # Simplified query safely handling counts
    raw_query = (
        select(Objection)
        .join(Conversation, Objection.conversation_id == Conversation.id)
        .where(Conversation.organization_id == current_user.organization_id)
    )
    res = await db.execute(raw_query)
    objections = res.scalars().all()

    stats: dict[str, dict] = {}
    for obj in objections:
        cat = obj.category or "other"
        if cat not in stats:
            stats[cat] = {"total": 0, "resolved": 0}
        stats[cat]["total"] += 1
        if obj.was_resolved:
            stats[cat]["resolved"] += 1

    return [
        ObjectionSummary(
            category=cat,
            count=data["total"],
            resolved_count=data["resolved"],
            unresolved_count=data["total"] - data["resolved"],
        )
        for cat, data in stats.items()
    ]
