"""
Sales Pipeline & Objections API Router.

GET   /api/v1/sales/pipeline                 — Leads (sales conversations) with AI scores and next action
PATCH /api/v1/sales/leads/{conversation_id}  — Move a lead to another pipeline stage
GET   /api/v1/sales/objections               — Objection matrix by category and resolution

Leads come from conversation intelligence: each conversation the sales agent analyzed is
one lead. People can correct the stage; the change is audit-logged with the AI's value.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import conversation_scope
from app.core.dependencies import get_current_user, get_db
from app.db.models import AuditLog, Conversation, Objection, Recommendation, SalesInsight, User

router = APIRouter(prefix="/sales", tags=["Sales Intelligence"])

PIPELINE_STAGES = ("new", "contacted", "qualified", "demo", "proposal", "negotiation", "won", "lost")
_PRIORITY_RANK = {"high": 0, "medium": 1, "low": 2}


class SalesLeadItem(BaseModel):
    conversation_id: str
    title: str
    lead_score: Optional[int]
    purchase_intent: Optional[str]
    deal_health: Optional[str]
    pipeline_stage: Optional[str]
    budget_range: Optional[str]
    timeline: Optional[str] = None
    decision_maker_present: bool = False
    closing_probability: Optional[float] = None
    next_action: Optional[str] = None
    owner_name: Optional[str] = None
    last_activity_at: str
    created_at: str


class UpdateLeadRequest(BaseModel):
    stage: str


class ObjectionSummary(BaseModel):
    category: str
    count: int
    resolved_count: int
    unresolved_count: int


async def _next_actions(db: AsyncSession, conversation_ids: list[str]) -> dict[str, str]:
    """Highest-priority AI recommendation per conversation."""
    if not conversation_ids:
        return {}
    recs = (await db.execute(
        select(Recommendation).where(Recommendation.conversation_id.in_(conversation_ids))
    )).scalars().all()
    best: dict[str, Recommendation] = {}
    for rec in recs:
        current = best.get(rec.conversation_id)
        if current is None or _PRIORITY_RANK.get(rec.priority, 3) < _PRIORITY_RANK.get(current.priority, 3):
            best[rec.conversation_id] = rec
    return {cid: rec.action for cid, rec in best.items()}


def _to_item(conv: Conversation, sales: SalesInsight, owner: Optional[str], next_action: Optional[str]) -> SalesLeadItem:
    return SalesLeadItem(
        conversation_id=conv.id,
        title=conv.title,
        lead_score=sales.lead_score,
        purchase_intent=sales.purchase_intent,
        deal_health=sales.deal_health,
        pipeline_stage=sales.stage,
        budget_range=sales.budget_range,
        timeline=sales.timeline,
        decision_maker_present=bool(sales.decision_maker_present),
        closing_probability=sales.closing_probability,
        next_action=next_action,
        owner_name=owner,
        last_activity_at=(conv.occurred_at or conv.created_at).isoformat(),
        created_at=conv.created_at.isoformat(),
    )


@router.get("/pipeline", response_model=list[SalesLeadItem])
async def get_sales_pipeline(
    stage: Optional[str] = Query(None),
    min_score: Optional[int] = Query(None, ge=0, le=100),
    purchase_intent: Optional[str] = Query(None),
    deal_health: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Leads with lead score, intent, stage, deal health, last activity and next action."""
    query = (
        select(Conversation, SalesInsight, User.full_name)
        .join(SalesInsight, Conversation.id == SalesInsight.conversation_id)
        .join(User, Conversation.created_by == User.id, isouter=True)
        .where(*conversation_scope(current_user))
    )
    if stage:
        query = query.where(SalesInsight.stage == stage)
    if min_score is not None:
        query = query.where(SalesInsight.lead_score >= min_score)
    if purchase_intent:
        query = query.where(SalesInsight.purchase_intent == purchase_intent)
    if deal_health:
        query = query.where(SalesInsight.deal_health == deal_health)
    if search:
        query = query.where(Conversation.title.ilike(f"%{search}%"))

    rows = (await db.execute(query.order_by(SalesInsight.lead_score.desc().nullslast()))).all()
    actions = await _next_actions(db, [conv.id for conv, _, _ in rows])
    return [_to_item(conv, sales, owner, actions.get(conv.id)) for conv, sales, owner in rows]


@router.patch("/leads/{conversation_id}", response_model=SalesLeadItem)
async def update_lead_stage(
    conversation_id: str,
    payload: UpdateLeadRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Move a lead to another pipeline stage (overrides the AI's stage)."""
    if payload.stage not in PIPELINE_STAGES:
        raise HTTPException(status_code=400, detail=f"Stage must be one of: {', '.join(PIPELINE_STAGES)}")
    row = (await db.execute(
        select(Conversation, SalesInsight, User.full_name)
        .join(SalesInsight, Conversation.id == SalesInsight.conversation_id)
        .join(User, Conversation.created_by == User.id, isouter=True)
        .where(Conversation.id == conversation_id, *conversation_scope(current_user))
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Lead not found")
    conv, sales, owner = row

    previous = sales.stage
    sales.stage = payload.stage
    db.add(AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="lead_stage_change",
        resource_type="conversation",
        resource_id=conversation_id,
        details={"from": previous, "to": payload.stage},
    ))
    await db.commit()
    actions = await _next_actions(db, [conversation_id])
    return _to_item(conv, sales, owner, actions.get(conversation_id))


@router.get("/objections", response_model=list[ObjectionSummary])
async def get_objection_matrix(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Objection frequency and resolution across the conversations you can see."""
    category = func.coalesce(Objection.category, "other")
    res = await db.execute(
        select(
            category.label("category"),
            func.count(Objection.id).label("total"),
            func.sum(case((Objection.was_resolved.is_(True), 1), else_=0)).label("resolved"),
        )
        .join(Conversation, Objection.conversation_id == Conversation.id)
        .where(*conversation_scope(current_user))
        .group_by(category)
        .order_by(func.count(Objection.id).desc())
    )
    return [
        ObjectionSummary(
            category=row.category,
            count=row.total,
            resolved_count=row.resolved or 0,
            unresolved_count=row.total - (row.resolved or 0),
        )
        for row in res.all()
    ]
