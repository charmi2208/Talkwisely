"""
Users & Organization Management API Router.

GET   /api/v1/users/me       — Current user profile
GET   /api/v1/users          — List team members (Admin / Manager only)
PATCH /api/v1/users/{id}/role — Update user role
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.db.models import User, Role

router = APIRouter(prefix="/users", tags=["Users & Organization Team"])


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    organization_id: str
    avatar_url: Optional[str] = None
    created_at: str

    class Config:
        from_attributes = True


class UpdateRoleRequest(BaseModel):
    role: str  # admin | manager | agent


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(current_user=Depends(get_current_user)):
    """Get current authenticated user profile."""
    return UserProfileResponse(
        id=current_user.id,
        email=current_user.email,
        full_name=current_user.full_name,
        role=current_user.role.name if hasattr(current_user.role, 'name') else str(current_user.role),
        organization_id=current_user.organization_id,
        avatar_url=current_user.avatar_url,
        created_at=current_user.created_at.isoformat(),
    )


@router.get("", response_model=list[UserProfileResponse])
async def list_team_members(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List team members in the current user's organization."""
    query = (
        select(User)
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.created_at.desc())
    )
    res = await db.execute(query)
    users = res.scalars().all()

    items = []
    for u in users:
        role_str = u.role.name if hasattr(u.role, 'name') else str(u.role or "agent")
        items.append(
            UserProfileResponse(
                id=u.id,
                email=u.email,
                full_name=u.full_name,
                role=role_str,
                organization_id=u.organization_id,
                avatar_url=u.avatar_url,
                created_at=u.created_at.isoformat(),
            )
        )

    return items


@router.patch("/{user_id}/role", response_model=UserProfileResponse)
async def update_user_role(
    user_id: str,
    payload: UpdateRoleRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update team member role (Admin only)."""
    current_role = current_user.role.name if hasattr(current_user.role, 'name') else str(current_user.role)
    if current_role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required to update user roles")

    res = await db.execute(
        select(User).where(
            User.id == user_id,
            User.organization_id == current_user.organization_id,
        )
    )
    user_obj = res.scalar_one_or_none()
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    # Find role entity if using Role table or set directly
    res_role = await db.execute(select(Role).where(Role.name == payload.role))
    role_obj = res_role.scalar_one_or_none()

    if role_obj:
        user_obj.role_id = role_obj.id

    await db.commit()
    await db.refresh(user_obj)

    return UserProfileResponse(
        id=user_obj.id,
        email=user_obj.email,
        full_name=user_obj.full_name,
        role=payload.role,
        organization_id=user_obj.organization_id,
        avatar_url=user_obj.avatar_url,
        created_at=user_obj.created_at.isoformat(),
    )
