"""
Meetings Intelligence API Router.

GET /api/v1/meetings               — List meetings with minutes and decisions
GET /api/v1/meetings/{id}/minutes  — Get meeting minutes formatted in Markdown
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.db.models import Conversation, MeetingMinutes

router = APIRouter(prefix="/meetings", tags=["Meeting Intelligence"])


class MeetingItem(BaseModel):
    conversation_id: str
    title: str
    objective: Optional[str]
    participants_summary: Optional[str]
    decisions_count: int
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
    formatted_markdown: str


@router.get("", response_model=list[MeetingItem])
async def list_meetings(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List meetings with generated meeting minutes."""
    query = (
        select(Conversation, MeetingMinutes)
        .join(MeetingMinutes, Conversation.id == MeetingMinutes.conversation_id)
        .where(Conversation.organization_id == current_user.organization_id)
        .order_by(Conversation.created_at.desc())
    )
    res = await db.execute(query)
    rows = res.all()

    items = []
    for conv, minutes in rows:
        decisions_list = minutes.decisions or []
        items.append(
            MeetingItem(
                conversation_id=conv.id,
                title=conv.title,
                objective=minutes.objective,
                participants_summary=minutes.participants_summary,
                decisions_count=len(decisions_list),
                created_at=conv.created_at.isoformat(),
            )
        )

    return items


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
            Conversation.organization_id == current_user.organization_id,
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
        formatted_markdown=minutes.formatted_markdown or "# Meeting Minutes\n\nNo formatted markdown available.",
    )
