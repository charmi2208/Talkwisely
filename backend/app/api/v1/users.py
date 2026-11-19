"""
Users & Organization Management API Router.

GET    /api/v1/users/me              — Current user profile
PATCH  /api/v1/users/me              — Update your name
POST   /api/v1/users/me/password     — Change your password
GET    /api/v1/users/me/preferences  — Your preferences (with defaults)
PUT    /api/v1/users/me/preferences  — Save preferences
GET    /api/v1/users                 — List team members (admin, manager)
POST   /api/v1/users                 — Add a team member with a temporary password (admin)
PATCH  /api/v1/users/{id}            — Rename, deactivate or reactivate a member (admin)
PATCH  /api/v1/users/{id}/role       — Change a member's role (admin)
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, EmailStr, Field
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.access import ROLE_PRIORITY, primary_role
from app.core.dependencies import get_current_user, get_db, require_roles
from app.core.preferences import DEFAULT_PREFERENCES, effective_preferences
from app.core.security import hash_password, verify_password
from app.db.models import AuditLog, Conversation, Organization, Role, User, UserRole

router = APIRouter(prefix="/users", tags=["Users & Organization Team"])

MIN_PASSWORD_LENGTH = 8


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    role: str
    organization_id: str
    organization_name: Optional[str] = None
    avatar_url: Optional[str] = None
    is_active: bool = True
    last_login_at: Optional[str] = None
    conversation_count: Optional[int] = None
    created_at: str


class UpdateRoleRequest(BaseModel):
    role: str  # admin | manager | agent


class UpdateProfileRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=255)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class CreateMemberRequest(BaseModel):
    email: EmailStr
    full_name: str = Field(min_length=1, max_length=255)
    role: str = "agent"
    temporary_password: str = Field(min_length=MIN_PASSWORD_LENGTH)


class UpdateMemberRequest(BaseModel):
    full_name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    is_active: Optional[bool] = None


class PreferencesPayload(BaseModel):
    auto_action_items: Optional[bool] = None
    lead_intent_alerts: Optional[bool] = None
    pbx_auto_sync: Optional[bool] = None


def _to_profile(user: User, conversation_count: int | None = None, organization_name: str | None = None) -> UserProfileResponse:
    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        role=primary_role(user),
        organization_id=user.organization_id,
        organization_name=organization_name,
        avatar_url=user.avatar_url,
        is_active=user.is_active,
        last_login_at=user.last_login_at.isoformat() if user.last_login_at else None,
        conversation_count=conversation_count,
        created_at=user.created_at.isoformat(),
    )


async def _load_member(db: AsyncSession, user_id: str, organization_id: str) -> User:
    user = (await db.execute(
        select(User)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .where(User.id == user_id, User.organization_id == organization_id)
        .execution_options(populate_existing=True)  # pick up role changes made in this session
    )).scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


async def _role_or_400(db: AsyncSession, name: str) -> Role:
    if name not in ROLE_PRIORITY:
        raise HTTPException(status_code=400, detail=f"Role must be one of: {', '.join(ROLE_PRIORITY)}")
    role = (await db.execute(select(Role).where(Role.name == name))).scalar_one_or_none()
    if not role:
        raise HTTPException(status_code=400, detail=f"Role '{name}' is not configured")
    return role


async def _active_admin_count(db: AsyncSession, organization_id: str) -> int:
    return (await db.execute(
        select(func.count(User.id))
        .join(UserRole, UserRole.user_id == User.id)
        .join(Role, Role.id == UserRole.role_id)
        .where(User.organization_id == organization_id, User.is_active.is_(True), Role.name == "admin")
    )).scalar_one()


def _audit(db: AsyncSession, actor: User, action: str, target_id: str, details: dict | None = None) -> None:
    db.add(AuditLog(
        organization_id=actor.organization_id,
        user_id=actor.id,
        action=action,
        resource_type="user",
        resource_id=target_id,
        details=details or {},
    ))


# ---------------------------------------------------------------------------
# Your own account
# ---------------------------------------------------------------------------

@router.get("/me", response_model=UserProfileResponse)
async def get_my_profile(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Current authenticated user's profile."""
    org = await db.get(Organization, current_user.organization_id)
    return _to_profile(current_user, organization_name=org.name if org else None)


@router.patch("/me", response_model=UserProfileResponse)
async def update_my_profile(
    payload: UpdateProfileRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Update your display name."""
    current_user.full_name = payload.full_name.strip()
    await db.commit()
    org = await db.get(Organization, current_user.organization_id)
    return _to_profile(current_user, organization_name=org.name if org else None)


@router.post("/me/password", status_code=status.HTTP_204_NO_CONTENT)
async def change_my_password(
    payload: ChangePasswordRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Change your password after confirming the current one."""
    if not verify_password(payload.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Current password is incorrect")
    if payload.current_password == payload.new_password:
        raise HTTPException(status_code=400, detail="Choose a password you haven't used here before")
    current_user.hashed_password = hash_password(payload.new_password)
    _audit(db, current_user, "password_change", current_user.id)
    await db.commit()


@router.get("/me/preferences")
async def get_my_preferences(current_user=Depends(get_current_user)):
    """Your preferences, with defaults filled in."""
    return effective_preferences(current_user.preferences)


@router.put("/me/preferences")
async def update_my_preferences(
    payload: PreferencesPayload,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Save preferences. Only the keys you send change."""
    prefs = effective_preferences(current_user.preferences)
    prefs.update({k: v for k, v in payload.model_dump(exclude_none=True).items() if k in DEFAULT_PREFERENCES})
    current_user.preferences = prefs  # reassign so SQLAlchemy sees the JSON change
    await db.commit()
    return prefs


# ---------------------------------------------------------------------------
# Team management
# ---------------------------------------------------------------------------

@router.get("", response_model=list[UserProfileResponse])
async def list_team_members(
    current_user=Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Team members in your organization with how many conversations each uploaded."""
    users = (await db.execute(
        select(User)
        .options(selectinload(User.user_roles).selectinload(UserRole.role))
        .where(User.organization_id == current_user.organization_id)
        .order_by(User.created_at.desc())
    )).scalars().all()
    counts = dict((await db.execute(
        select(Conversation.created_by, func.count(Conversation.id))
        .where(Conversation.organization_id == current_user.organization_id)
        .group_by(Conversation.created_by)
    )).all())
    return [_to_profile(u, conversation_count=counts.get(u.id, 0)) for u in users]


@router.post("", response_model=UserProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_team_member(
    payload: CreateMemberRequest,
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Add a member with a temporary password you share with them (no email is sent)."""
    email = payload.email.lower()
    if (await db.execute(select(User.id).where(User.email == email))).first():
        raise HTTPException(status_code=409, detail="An account with this email already exists")
    role = await _role_or_400(db, payload.role)

    user = User(
        organization_id=current_user.organization_id,
        email=email,
        hashed_password=hash_password(payload.temporary_password),
        full_name=payload.full_name.strip(),
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    await db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id))
    _audit(db, current_user, "user_create", user.id, {"email": email, "role": role.name})
    await db.commit()
    return _to_profile(await _load_member(db, user.id, current_user.organization_id), conversation_count=0)


@router.patch("/{user_id}", response_model=UserProfileResponse)
async def update_team_member(
    user_id: str,
    payload: UpdateMemberRequest,
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Rename a member, or deactivate/reactivate their account."""
    user = await _load_member(db, user_id, current_user.organization_id)

    if payload.is_active is False and user.is_active:
        if user.id == current_user.id:
            raise HTTPException(status_code=400, detail="You can't deactivate your own account")
        if primary_role(user) == "admin" and await _active_admin_count(db, current_user.organization_id) <= 1:
            raise HTTPException(status_code=400, detail="The organization needs at least one active admin")
    if payload.full_name is not None:
        user.full_name = payload.full_name.strip()
    if payload.is_active is not None:
        user.is_active = payload.is_active

    _audit(db, current_user, "user_update", user.id, payload.model_dump(exclude_none=True))
    await db.commit()
    return _to_profile(user)


@router.patch("/{user_id}/role", response_model=UserProfileResponse)
async def update_user_role(
    user_id: str,
    payload: UpdateRoleRequest,
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Update a team member's role (admin only)."""
    role = await _role_or_400(db, payload.role)
    if user_id == current_user.id and payload.role != "admin":
        raise HTTPException(status_code=400, detail="You can't remove your own admin role")

    user = await _load_member(db, user_id, current_user.organization_id)

    # A user holds exactly one role; replace any existing assignments
    await db.execute(delete(UserRole).where(UserRole.user_id == user.id))
    db.add(UserRole(user_id=user.id, role_id=role.id))
    _audit(db, current_user, "role_change", user.id, {"role": role.name})
    await db.commit()

    return _to_profile(await _load_member(db, user.id, current_user.organization_id))
