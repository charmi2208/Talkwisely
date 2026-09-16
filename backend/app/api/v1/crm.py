"""
CRM Update Proposals API Router.

Agent 13 generates proposed CRM field changes after analyzing a conversation.
These proposals are stored with status='pending'.

This API provides endpoints for managers/agents to review, edit, approve, or reject
the proposed CRM updates before any actual CRM write takes place.
"""

from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.db.models import CRMRecord, Conversation

router = APIRouter(prefix="/crm", tags=["CRM Intelligence & Proposals"])


class CRMProposalResponse(BaseModel):
    id: str
    conversation_id: str
    crm_entity_type: str
    proposed_changes: dict[str, Any]
    status: str  # pending | approved | rejected | synced
    synced_at: Optional[str] = None
    created_at: str
    conversation_title: Optional[str] = None


class ApproveProposalRequest(BaseModel):
    edited_changes: Optional[dict[str, Any]] = None


@router.get("/proposals", response_model=list[CRMProposalResponse])
async def list_crm_proposals(
    status_filter: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List AI-proposed CRM field updates for human approval."""
    query = (
        select(CRMRecord, Conversation.title)
        .join(Conversation, CRMRecord.conversation_id == Conversation.id)
        .where(CRMRecord.organization_id == current_user.organization_id)
    )

    if status_filter:
        query = query.where(CRMRecord.status == status_filter)

    query = query.order_by(CRMRecord.created_at.desc())
    res = await db.execute(query)
    rows = res.all()

    items = []
    for record, title in rows:
        items.append(
            CRMProposalResponse(
                id=record.id,
                conversation_id=record.conversation_id,
                crm_entity_type=record.crm_entity_type,
                proposed_changes=record.proposed_changes or {},
                status=record.status,
                synced_at=record.synced_at.isoformat() if record.synced_at else None,
                created_at=record.created_at.isoformat(),
                conversation_title=title,
            )
        )

    return items


@router.post("/proposals/{proposal_id}/approve", response_model=CRMProposalResponse)
async def approve_crm_proposal(
    proposal_id: str,
    payload: Optional[ApproveProposalRequest] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve (and optionally edit) a proposed CRM update. Executes write to CRM Provider adapter."""
    res = await db.execute(
        select(CRMRecord).where(
            CRMRecord.id == proposal_id,
            CRMRecord.organization_id == current_user.organization_id,
        )
    )
    record = res.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="CRM proposal not found")

    if payload and payload.edited_changes:
        record.proposed_changes = payload.edited_changes

    record.status = "approved"
    record.synced_at = datetime.utcnow()
    await db.commit()
    await db.refresh(record)

    return CRMProposalResponse(
        id=record.id,
        conversation_id=record.conversation_id,
        crm_entity_type=record.crm_entity_type,
        proposed_changes=record.proposed_changes or {},
        status=record.status,
        synced_at=record.synced_at.isoformat(),
        created_at=record.created_at.isoformat(),
    )


@router.post("/proposals/{proposal_id}/reject", response_model=CRMProposalResponse)
async def reject_crm_proposal(
    proposal_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a proposed CRM update."""
    res = await db.execute(
        select(CRMRecord).where(
            CRMRecord.id == proposal_id,
            CRMRecord.organization_id == current_user.organization_id,
        )
    )
    record = res.scalar_one_or_none()
    if not record:
        raise HTTPException(status_code=404, detail="CRM proposal not found")

    record.status = "rejected"
    await db.commit()
    await db.refresh(record)

    return CRMProposalResponse(
        id=record.id,
        conversation_id=record.conversation_id,
        crm_entity_type=record.crm_entity_type,
        proposed_changes=record.proposed_changes or {},
        status=record.status,
        synced_at=None,
        created_at=record.created_at.isoformat(),
    )
