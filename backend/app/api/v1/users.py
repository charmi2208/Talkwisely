"""
Users & Organization Management API Router.

GET   /api/v1/users/me       — Current user profile
GET   /api/v1/users          — List team members (Admin / Manager only)
PATCH /api/v1/users/{id}/role — Update user role
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.dependencies import get_current_user, get_db, require_roles
from app.db.models import Role, User, UserRole

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


# Highest-privilege role wins when a user holds several
_ROLE_PRIORITY = ("admin", "manager", "agent")


def _primary_role(user: User) -> str:
    names = {ur.role.name for ur in user.user_roles if ur.role}
    return next((r for r in _ROLE_PRIORITY if r in names), "agent")


def _to_profile(user: User, role: str) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=role,
        organization_id=user.organization_id,
        avatar_url=user.avatar_url,
        created_at=user.created_at.isoformat(),
    )


async def _load_user_with_roles(db: AsyncSession, user_id: str, organization_id: str) -> User | None:
    res = await db.execute(
        select(User)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .where(User.id == user_id, User.organization_id == organization_id)
    )
    return res.scalar_one_or_none()


@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Get current authenticated user profile."""
    user = await _load_user_with_roles(db, current_user.id, current_user.organization_id)
    return _to_profile(user, _primary_role(user))


@router.get("", response_model=list[UserProfileResponse])
async def list_team_members(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List team members in the current user's organization."""
    res = await db.execute(
        select(User)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.created_at.desc())
    )
    return [_to_profile(u, _primary_role(u)) for u in res.scalars().all()]


@router.patch("/{user_id}/role", response_model=UserProfileResponse)
async def update_user_role(
    user_id: str,
    payload: UpdateRoleRequest,
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update team member role (Admin only)."""
    if payload.role not in _ROLE_PRIORITY:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(_ROLE_PRIORITY)}")
    if user_id == current_user.id and payload.role != "admin":
        raise HTTPException(status_code=400, detail="You can't remove your own admin role")

    user_obj = await _load_user_with_roles(db, user_id, current_user.organization_id)
    if not user_obj:
        raise HTTPException(status_code=404, detail="User not found")

    role_obj = (await db.execute(select(Role).where(Role.name == payload.role))).scalar_one_or_none()
    if not role_obj:
        raise HTTPException(status_code=400, detail=f"Role '{payload.role}' is not configured")

    # A user holds exactly one role; replace any existing assignments
    await db.execute(delete(UserRole).where(UserRole.user_id == user_obj.id))
    db.add(UserRole(user_id=user_obj.id, role_id=role_obj.id))
    await db.commit()

    return _to_profile(user_obj, payload.role)
