"""
Meetings Intelligence API Router.

GET /api/v1/meetings               — List meetings with minutes and decisions
GET /api/v1/meetings/{id}/minutes  — Get meeting minutes formatted in Markdown
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.analytics import MEETING_TYPES
from app.core.access import conversation_scope
from app.core.dependencies import get_current_user, get_db
from app.db.models import Conversation, MeetingMinutes

router = APIRouter(prefix="/meetings", tags=["Meeting Intelligence"])


class MeetingItem(BaseModel):
    conversation_id: str
    title: str
    conversation_type: str
    objective: Optional[str]
    participants_summary: Optional[str]
    decisions_count: int
    action_items_count: int
    open_questions_count: int
    next_meeting: Optional[str] = None
    duration_seconds: Optional[int] = None
    occurred_at: Optional[str] = None
    created_at: str


class MeetingMinutesResponse(BaseModel):
    conversation_id: str
    title: str
    objective: Optional[str]
    participants_summary: Optional[str]
    discussion_points: list[str]
    decisions: list[str]
    action_items_summary: list[str]
    open_questions: list[str]
    risks: list[str]
    next_steps: list[str]
    next_meeting: Optional[str] = None
    formatted_markdown: str


@router.get("", response_model=list[MeetingItem])
async def list_meetings(
    meetings_only: bool = Query(False, description="Only internal and client meetings"),
    search: Optional[str] = Query(None),
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Conversations with generated meeting minutes, newest first."""
    query = (
        select(Conversation, MeetingMinutes)
        .join(MeetingMinutes, Conversation.id == MeetingMinutes.conversation_id)
        .where(*conversation_scope(current_user))
    )
    if meetings_only:
        query = query.where(Conversation.conversation_type.in_(MEETING_TYPES))
    if search:
        query = query.where(Conversation.title.ilike(f"%{search}%"))
    rows = (await db.execute(query.order_by(Conversation.created_at.desc()))).all()

    return [
        MeetingItem(
            conversation_id=conv.id,
            title=conv.title,
            conversation_type=conv.conversation_type,
            objective=minutes.objective,
            participants_summary=minutes.participants_summary,
            decisions_count=len(minutes.decisions or []),
            action_items_count=len(minutes.action_items_summary or []),
            open_questions_count=len(minutes.open_questions or []),
            next_meeting=minutes.next_meeting,
            duration_seconds=conv.duration_seconds,
            occurred_at=conv.occurred_at.isoformat() if conv.occurred_at else None,
            created_at=conv.created_at.isoformat(),
        )
        for conv, minutes in rows
    ]


@router.get("/{conversation_id}/minutes", response_model=MeetingMinutesResponse)
async def get_meeting_minutes(
    conversation_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get complete meeting minutes formatted for export."""
    query = (
        select(Conversation, MeetingMinutes)
        .join(MeetingMinutes, Conversation.id == MeetingMinutes.conversation_id)
        .where(
            Conversation.id == conversation_id,
            *conversation_scope(current_user),
        )
    )
    res = await db.execute(query)
    row = res.first()
    if not row:
        raise HTTPException(status_code=404, detail="Meeting minutes not found")

    conv, minutes = row

    return MeetingMinutesResponse(
        conversation_id=conv.id,
        title=conv.title,
        objective=minutes.objective,
        participants_summary=minutes.participants_summary,
        discussion_points=minutes.discussion_points or [],
        decisions=minutes.decisions or [],
        action_items_summary=minutes.action_items_summary or [],
        open_questions=minutes.open_questions or [],
        risks=minutes.risks or [],
        next_steps=minutes.next_steps or [],
        next_meeting=minutes.next_meeting,
        formatted_markdown=minutes.formatted_markdown or "# Meeting Minutes\n\nNo formatted markdown available.",
    )
