"""
In-App Notifications API Router.

GET  /api/v1/notifications          — List user notifications
POST /api/v1/notifications/{id}/read — Mark notification as read
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.db.models import Notification

router = APIRouter(prefix="/notifications", tags=["Notifications"])


class NotificationResponse(BaseModel):
    id: str
    conversation_id: Optional[str]
    type: str  # processing_complete | processing_failed | task_due | high_intent_lead
    title: str
    message: str
    is_read: bool
    created_at: str

    class Config:
        from_attributes = True


@router.get("", response_model=list[NotificationResponse])
async def list_notifications(
    unread_only: bool = False,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List in-app notifications for the authenticated user."""
    query = select(Notification).where(Notification.user_id == current_user.id)
    if unread_only:
        query = query.where(Notification.is_read == False)

    query = query.order_by(Notification.created_at.desc()).limit(50)
    res = await db.execute(query)
    notifications = res.scalars().all()

    return [
        NotificationResponse(
            id=n.id,
            conversation_id=n.conversation_id,
            type=n.type,
            title=n.title,
            message=n.message,
            is_read=n.is_read,
            created_at=n.created_at.isoformat(),
        )
        for n in notifications
    ]


@router.post("/{notification_id}/read", response_model=NotificationResponse)
async def mark_notification_read(
    notification_id: str,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Mark notification as read."""
    res = await db.execute(
        select(Notification).where(
            Notification.id == notification_id,
            Notification.user_id == current_user.id,
        )
    )
    notification = res.scalar_one_or_none()
    if not notification:
        raise HTTPException(status_code=404, detail="Notification not found")

    notification.is_read = True
    await db.commit()
    await db.refresh(notification)

    return NotificationResponse(
        id=notification.id,
        conversation_id=notification.conversation_id,
        type=notification.type,
        title=notification.title,
        message=notification.message,
        is_read=notification.is_read,
        created_at=notification.created_at.isoformat(),
    )
