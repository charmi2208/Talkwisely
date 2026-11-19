"""
Action Items (Task Management) API Router.

GET    /api/v1/action-items           — List action items with filtering
POST   /api/v1/action-items           — Create a task (optionally linked to a conversation)
PATCH  /api/v1/action-items/{id}      — Update description, status, priority, due date, owner
DELETE /api/v1/action-items/{id}      — Delete a task

Tasks come from two places: the action item agent (linked to a conversation) and people
adding them by hand (``conversation_id`` may be null). Agents see tasks from their own
conversations plus the ones they created; admins and managers see the whole organization.

Open tasks whose due date has passed are reported (and stored) as ``overdue``.
"""

import uuid
from datetime import date, datetime, time
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel
from sqlalchemy import and_, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.access import conversation_scope, is_privileged
from app.core.dependencies import get_current_user, get_db
from app.db.models import ActionItem, Conversation

router = APIRouter(prefix="/action-items", tags=["Action Items"])

PRIORITIES = ("low", "medium", "high", "urgent")
STATUSES = ("pending", "in_progress", "completed", "overdue")


class ActionItemResponse(BaseModel):
    id: str
    conversation_id: Optional[str]
    description: str
    owner: Optional[str]
    due_date: Optional[str]
    due_at: Optional[datetime] = None
    priority: str
    status: str
    source_timestamp: Optional[float]
    related_topic: Optional[str]
    created_at: datetime
    completed_at: Optional[datetime] = None
    is_ai_generated: bool = True
    conversation_title: Optional[str] = None


class CreateActionItemRequest(BaseModel):
    conversation_id: Optional[str] = None
    description: str
    owner: Optional[str] = None
    due_date: Optional[str] = None  # ISO date (YYYY-MM-DD) or free text such as "Friday"
    priority: str = "medium"


class UpdateActionItemRequest(BaseModel):
    description: Optional[str] = None
    owner: Optional[str] = None
    due_date: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[str] = None


def _parse_due(value: Optional[str]) -> Optional[datetime]:
    """End of the given day for ISO dates; None for free text the AI copied from the call."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        pass
    try:
        return datetime.combine(date.fromisoformat(value), time(23, 59, 59))
    except ValueError:
        return None


def visible_action_items(user) -> list:
    """Conditions for the tasks ``user`` may see (query must outer-join Conversation)."""
    if is_privileged(user):
        return [ActionItem.organization_id == user.organization_id]
    return [
        ActionItem.organization_id == user.organization_id,
        or_(
            and_(ActionItem.conversation_id.is_not(None), *conversation_scope(user)),
            ActionItem.created_by == user.id,
        ),
    ]


def _refresh_overdue(item: ActionItem, now: datetime) -> None:
    if item.status in ("pending", "in_progress") and item.due_date_parsed and item.due_date_parsed < now:
        item.status = "overdue"
    elif item.status == "overdue" and (not item.due_date_parsed or item.due_date_parsed >= now):
        item.status = "pending"


def _to_response(item: ActionItem, title: Optional[str] = None) -> ActionItemResponse:
    return ActionItemResponse(
        id=item.id,
        conversation_id=item.conversation_id,
        description=item.description,
        owner=item.owner,
        due_date=item.due_date,
        due_at=item.due_date_parsed,
        priority=item.priority,
        status=item.status,
        source_timestamp=item.source_timestamp,
        related_topic=item.related_topic,
        created_at=item.created_at,
        completed_at=item.completed_at,
        is_ai_generated=item.created_by is None,
        conversation_title=title,
    )


async def _get_item(db: AsyncSession, item_id: str, user) -> tuple[ActionItem, Optional[str]]:
    row = (await db.execute(
        select(ActionItem, Conversation.title)
        .outerjoin(Conversation, ActionItem.conversation_id == Conversation.id)
        .where(ActionItem.id == item_id, *visible_action_items(user))
    )).first()
    if not row:
        raise HTTPException(status_code=404, detail="Action item not found")
    return row[0], row[1]


def _check_choice(value: Optional[str], allowed: tuple[str, ...], field: str) -> None:
    if value is not None and value not in allowed:
        raise HTTPException(status_code=422, detail=f"{field} must be one of: {', '.join(allowed)}")


@router.get("", response_model=list[ActionItemResponse])
async def list_action_items(
    priority: Optional[str] = Query(None),
    status_filter: Optional[str] = Query(None, alias="status"),
    conversation_id: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List the tasks you can see, newest first."""
    rows = (await db.execute(
        select(ActionItem, Conversation.title)
        .outerjoin(Conversation, ActionItem.conversation_id == Conversation.id)
        .where(*visible_action_items(current_user))
        .order_by(ActionItem.created_at.desc())
    )).all()

    now = datetime.utcnow()
    changed = False
    for item, _ in rows:
        before = item.status
        _refresh_overdue(item, now)
        changed |= item.status != before
    if changed:
        await db.commit()

    items = [
        (item, title) for item, title in rows
        if (not priority or item.priority == priority)
        and (not status_filter or item.status == status_filter)
        and (not conversation_id or item.conversation_id == conversation_id)
    ]
    return [_to_response(item, title) for item, title in items]


@router.post("", response_model=ActionItemResponse, status_code=status.HTTP_201_CREATED)
async def create_action_item(
    payload: CreateActionItemRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Create a task by hand, optionally linked to a conversation you can see."""
    _check_choice(payload.priority, PRIORITIES, "priority")
    if not payload.description.strip():
        raise HTTPException(status_code=422, detail="Describe the task")

    title = None
    if payload.conversation_id:
        conv = (await db.execute(
            select(Conversation).where(Conversation.id == payload.conversation_id, *conversation_scope(current_user))
        )).scalar_one_or_none()
        if not conv:
            raise HTTPException(status_code=404, detail="Conversation not found")
        title = conv.title

    item = ActionItem(
        id=str(uuid.uuid4()),
        organization_id=current_user.organization_id,
        conversation_id=payload.conversation_id,
        created_by=current_user.id,
        description=payload.description.strip(),
        owner=(payload.owner or "").strip() or None,
        due_date=payload.due_date,
        due_date_parsed=_parse_due(payload.due_date),
        priority=payload.priority,
        status="pending",
    )
    _refresh_overdue(item, datetime.utcnow())
    db.add(item)
    await db.commit()
    await db.refresh(item)
    return _to_response(item, title)


@router.patch("/{item_id}", response_model=ActionItemResponse)
async def update_action_item(
    item_id: str,
    payload: UpdateActionItemRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update a task's description, owner, due date, priority or status."""
    _check_choice(payload.priority, PRIORITIES, "priority")
    _check_choice(payload.status, STATUSES, "status")
    item, title = await _get_item(db, item_id, current_user)

    if payload.description is not None:
        if not payload.description.strip():
            raise HTTPException(status_code=422, detail="Describe the task")
        item.description = payload.description.strip()
    if payload.owner is not None:
        item.owner = payload.owner.strip() or None
    if payload.due_date is not None:
        item.due_date = payload.due_date or None
        item.due_date_parsed = _parse_due(payload.due_date)
    if payload.priority is not None:
        item.priority = payload.priority
    if payload.status is not None:
        item.status = payload.status
        item.completed_at = datetime.utcnow() if payload.status == "completed" else None
    _refresh_overdue(item, datetime.utcnow())

    await db.commit()
    await db.refresh(item)
    return _to_response(item, title)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_action_item(
    item_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Delete a task."""
    item, _ = await _get_item(db, item_id, current_user)
    await db.delete(item)
    await db.commit()
