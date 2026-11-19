"""
CRM Update Proposals API Router.

Agent 13 generates proposed CRM field changes after analyzing a conversation.
These proposals are stored with status='pending'.

This API provides endpoints for managers/agents to review, edit, approve, or reject
the proposed CRM updates before any actual CRM write takes place.
"""

from datetime import datetime
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import conversation_scope
from app.core.config import settings
from app.core.dependencies import get_current_user, get_db
from app.db.models import AuditLog, CRMRecord, Conversation
from app.integrations.crm.crm_adapter import CRMProvider, MockCRMProvider
from app.integrations.registry import get_integration, mark_synced

router = APIRouter(prefix="/crm", tags=["CRM Intelligence & Proposals"])


class CRMProposalResponse(BaseModel):
    id: str
    conversation_id: str
    crm_entity_type: str
    proposed_changes: dict[str, Any]
    status: str  # pending | rejected | applied
    approved_by: Optional[str] = None
    applied_at: Optional[str] = None
    created_at: str
    conversation_title: Optional[str] = None
    crm_provider: str


class ApproveProposalRequest(BaseModel):
    edited_changes: Optional[dict[str, Any]] = None


def get_crm_provider(integration=None) -> CRMProvider:
    """Return the organization's CRM adapter. Only the mock adapter is implemented so far."""
    provider = integration.provider if integration is not None else settings.crm_provider
    if provider == "mock":
        name = ((integration.config or {}).get("crm_name") if integration is not None else None) or "Salesforce"
        return MockCRMProvider(crm_name=f"{name} (mock)")
    raise HTTPException(
        status_code=501,
        detail=f"CRM provider '{provider}' is not implemented yet. Choose the mock CRM under Integrations.",
    )


def _to_response(record: CRMRecord, title: Optional[str] = None) -> CRMProposalResponse:
    return CRMProposalResponse(
        id=record.id,
        conversation_id=record.conversation_id,
        crm_entity_type=record.crm_entity_type or "lead",
        proposed_changes=record.proposed_changes or {},
        status=record.status,
        approved_by=record.approved_by,
        applied_at=record.applied_at.isoformat() if record.applied_at else None,
        created_at=record.created_at.isoformat(),
        conversation_title=title,
        crm_provider=settings.crm_provider,
    )


async def _get_pending_record(db: AsyncSession, proposal_id: str, user) -> tuple[CRMRecord, str]:
    res = await db.execute(
        select(CRMRecord, Conversation.title)
        .join(Conversation, CRMRecord.conversation_id == Conversation.id)
        .where(CRMRecord.id == proposal_id, *conversation_scope(user))
    )
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="CRM proposal not found")
    record, title = row
    if record.status != "pending":
        raise HTTPException(status_code=409, detail=f"Proposal is already {record.status}")
    return record, title


@router.get("/proposals", response_model=list[CRMProposalResponse])
async def list_crm_proposals(
    status_filter: Optional[str] = None,
    conversation_id: Optional[str] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List AI-proposed CRM field updates for human approval."""
    query = (
        select(CRMRecord, Conversation.title)
        .join(Conversation, CRMRecord.conversation_id == Conversation.id)
        .where(*conversation_scope(current_user))
    )

    if status_filter:
        query = query.where(CRMRecord.status == status_filter)
    if conversation_id:
        query = query.where(CRMRecord.conversation_id == conversation_id)

    query = query.order_by(CRMRecord.created_at.desc())
    res = await db.execute(query)
    return [_to_response(record, title) for record, title in res.all()]


@router.post("/proposals/{proposal_id}/approve", response_model=CRMProposalResponse)
async def approve_crm_proposal(
    proposal_id: str,
    payload: Optional[ApproveProposalRequest] = None,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Approve (and optionally edit) a proposed CRM update, then write it through the CRM adapter."""
    record, title = await _get_pending_record(db, proposal_id, current_user)
    integration = await get_integration(db, current_user.organization_id, "crm")
    if not integration.is_enabled:
        raise HTTPException(status_code=409, detail="The CRM integration is turned off. An admin can turn it on under Integrations.")
    provider = get_crm_provider(integration)

    if payload and payload.edited_changes:
        record.proposed_changes = payload.edited_changes

    # The write only happens after a human approved it
    entity_id = record.crm_entity_id or record.conversation_id
    if record.crm_entity_type in ("opportunity", "deal"):
        ok = await provider.update_opportunity(entity_id, record.proposed_changes or {})
    else:
        ok = await provider.update_lead(entity_id, record.proposed_changes or {})
    if not ok:
        await db.rollback()
        raise HTTPException(status_code=502, detail=f"{provider.provider_name} rejected the update. The proposal is still pending.")

    record.status = "applied"
    record.approved_by = current_user.id
    record.applied_at = datetime.utcnow()
    mark_synced(integration)
    db.add(AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="crm_approve",
        resource_type="crm_record",
        resource_id=record.id,
        details={"provider": provider.provider_name, "changes": record.proposed_changes, "edited": bool(payload and payload.edited_changes)},
    ))
    await db.commit()
    await db.refresh(record)
    return _to_response(record, title)


@router.post("/proposals/{proposal_id}/reject", response_model=CRMProposalResponse)
async def reject_crm_proposal(
    proposal_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Reject a proposed CRM update. Nothing is written to the CRM."""
    record, title = await _get_pending_record(db, proposal_id, current_user)

    record.status = "rejected"
    db.add(AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="crm_reject",
        resource_type="crm_record",
        resource_id=record.id,
    ))
    await db.commit()
    await db.refresh(record)
    return _to_response(record, title)
