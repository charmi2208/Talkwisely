"""
Action Items (Task Management) API Router.

GET    /api/v1/action-items           — List action items with filtering
POST   /api/v1/action-items           — Create manual action item
PATCH  /api/v1/action-items/{id}      — Update status, priority, due date, owner
DELETE /api/v1/action-items/{id}      — Delete action item
"""

import uuid
from datetime import datetime
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.db.models import ActionItem, Conversation

router = APIRouter(prefix="/action-items", tags=["Action Items"])


class ActionItemResponse(BaseModel):
    id: str
    conversation_id: Optional[str]
    description: str
    owner: Optional[str]
    due_date: Optional[str]
    priority: str
    status: str
    source_timestamp: Optional[float]
    related_topic: Optional[str]
    created_at: datetime
    conversation_title: Optional[str] = None

    class Config:
        from_attributes = True


class CreateActionItemRequest(BaseModel):
    conversation_id: Optional[str] = None
    description: str
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: str = "medium"  # low | medium | high | urgent


class UpdateActionItemRequest(BaseModel):
    description: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None  # pending | in_progress | completed | overdue


@router.get("", response_model=list[ActionItemResponse])
async def list_action_items(
    priority: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    conversation_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List action items for the current user's organization."""
    query = (
        select(ActionItem, Conversation.title)
        .outerjoin(Conversation, ActionItem.conversation_id == Conversation.id)
        .where(ActionItem.organization_id == current_user.organization_id)
    )

    if priority:
        query = query.where(ActionItem.priority == priority)
    if status_filter:
        query = query.where(ActionItem.status == status_filter)
    if conversation_id:
        query = query.where(ActionItem.conversation_id == conversation_id)

    query = query.order_by(ActionItem.created_at.desc())
    result = await db.execute(query)
    rows = result.all()

    items = []
    for item, conv_title in rows:
        resp = ActionItemResponse.model_validate(item)
        resp.conversation_title = conv_title
        items.append(resp)

    return items


@router.post("", response_model=ActionItemResponse, status_code=status.HTTP_201_CREATED)
async def create_action_item(
    payload: CreateActionItemRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Manually create an action item task."""
    item = ActionItem(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        conversation_id=payload.conversation_id,
        description=payload.description.strip(),
        owner=payload.owner,
        due_date=payload.due_date,
        priority=payload.priority,
        status="pending",
    )
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return ActionItemResponse.model_validate(item)


@router.patch("/{item_id}", response_model=ActionItemResponse)
async def update_action_item(
    item_id: str,
    payload: UpdateActionItemRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update action item status, priority, owner, or due date."""
    res = await db.execute(
        select(ActionItem).where(
            ActionItem.id == item_id,
            ActionItem.organization_id == current_user.organization_id,
        )
    )
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    if payload.description is not None:
        item.description = payload.description.strip()
    if payload.owner is not None:
        item.owner = payload.owner
    if payload.due_date is not None:
        item.due_date = payload.due_date
    if payload.priority is not None:
        item.priority = payload.priority
    if payload.status is not None:
        item.status = payload.status
        if payload.status == "completed":
            item.completed_at = datetime.utcnow()

    await db.commit()
    await db.refresh(item)
    return ActionItemResponse.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action_item(
    item_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete an action item."""
    res = await db.execute(
        select(ActionItem).where(
            ActionItem.id == item_id,
            ActionItem.organization_id == current_user.organization_id,
        )
    )
    item = res.scalar_one_or_none()
    if not item:
        raise HTTPException(status_code=404, detail="Action item not found")

    await db.delete(item)
    await db.commit()
