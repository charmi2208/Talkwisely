"""
Authentication API Routes.

POST /api/v1/auth/register  — Register new user
POST /api/v1/auth/login     — Login, returns JWT tokens
POST /api/v1/auth/refresh   — Refresh access token
GET  /api/v1/auth/me        — Get current user profile
"""

from datetime import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import Field, BaseModel, EmailStr
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.core.logging import get_logger
from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_refresh_token,
    hash_password,
    verify_password,
)
from app.db.models import AuditLog, Organization, Role, User, UserRole
from app.db.session import get_db

router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = get_logger("auth.routes")


# ---------------------------------------------------------------------------
# Pydantic schemas
# ---------------------------------------------------------------------------

class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)
    full_name: str = Field(min_length=1, max_length=255)
    organization_name: str | None = None
    organization_slug: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    user_id: str
    email: str
    full_name: str
    organization_id: str


class RefreshRequest(BaseModel):
    refresh_token: str


class UserProfileResponse(BaseModel):
    id: str
    email: str
    full_name: str
    organization_id: str
    organization_name: str
    roles: list[str]
    is_active: bool
    created_at: datetime


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def register(
    body: RegisterRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Register a new user and organization."""
    import uuid

    # Check email uniqueness
    existing = await db.execute(select(User).where(User.email == body.email))
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    # Create or find organization
    org_name = body.organization_name or f"{body.full_name}'s Organization"
    org_slug = body.organization_slug or org_name.lower().replace(" ", "-")[:50]

    # Ensure slug is unique
    slug_check = await db.execute(select(Organization).where(Organization.slug == org_slug))
    if slug_check.scalar_one_or_none():
        org_slug = f"{org_slug}-{str(uuid.uuid4())[:8]}"

    org = Organization(
        id=str(uuid.uuid4()),
        name=org_name,
        slug=org_slug,
    )
    db.add(org)
    await db.flush()

    # Create user
    user = User(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        email=body.email,
        hashed_password=hash_password(body.password),
        full_name=body.full_name,
        is_verified=True,  # Auto-verify for MVP
    )
    db.add(user)
    await db.flush()

    # Assign admin role (first user in org is always admin)
    admin_role = await db.execute(select(Role).where(Role.name == "admin"))
    admin_role_obj = admin_role.scalar_one_or_none()
    if admin_role_obj:
        user_role = UserRole(
            id=str(uuid.uuid4()),
            user_id=user.id,
            role_id=admin_role_obj.id,
        )
        db.add(user_role)

    # Audit log
    audit = AuditLog(
        id=str(uuid.uuid4()),
        organization_id=org.id,
        user_id=user.id,
        action="register",
        resource_type="user",
        resource_id=user.id,
        ip_address=request.client.host if request.client else None,
    )
    db.add(audit)
    await db.commit()

    logger.info("New user registered", user_id=user.id, org_id=org.id)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        organization_id=org.id,
    )


@router.post("/login", response_model=TokenResponse)
async def login(
    body: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Authenticate user and return JWT tokens."""
    import uuid

    # Find user by email
    result = await db.execute(select(User).where(func.lower(User.email) == body.email.lower()))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Contact your administrator.",
        )

    # Update last login
    user.last_login_at = datetime.utcnow()

    # Audit log
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        organization_id=user.organization_id,
        user_id=user.id,
        action="login",
        ip_address=request.client.host if request.client else None,
    ))
    await db.commit()

    logger.info("User logged in", user_id=user.id)

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        organization_id=user.organization_id,
    )


@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    body: RefreshRequest,
    db: AsyncSession = Depends(get_db),
):
    """Exchange a refresh token for new access + refresh tokens."""
    from jose import JWTError

    try:
        payload = decode_refresh_token(body.refresh_token)
        user_id = payload.get("sub")
        if not user_id:
            raise ValueError("Invalid token")
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="User not found")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        organization_id=user.organization_id,
    )


@router.get("/me", response_model=UserProfileResponse)
async def get_me(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Return the authenticated user's profile."""
    from sqlalchemy.orm import selectinload

    # Load with roles and org
    result = await db.execute(
        select(User)
        .options(
            selectinload(User.user_roles).selectinload(UserRole.role),
            selectinload(User.organization),
        )
        .where(User.id == current_user.id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    roles = [ur.role.name for ur in user.user_roles]

    return UserProfileResponse(
        id=user.id,
        email=user.email,
        full_name=user.full_name,
        organization_id=user.organization_id,
        organization_name=user.organization.name,
        roles=roles,
        is_active=user.is_active,
        created_at=user.created_at,
    )



# ---------------------------------------------------------------------------
# Forgot / reset password
# ---------------------------------------------------------------------------

class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


FORGOT_PASSWORD_MESSAGE = "If an account exists for that email, a password reset link has been sent."


@router.post("/forgot-password")
async def forgot_password(body: ForgotPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Email a password reset link valid for 30 minutes.

    The response is the same whether or not the account exists, so it can't be used to
    discover registered emails. With the mock email provider in development, nothing is
    delivered, so the link is returned as ``dev_reset_url`` to keep the flow testable.
    """
    from app.core.config import settings
    from app.core.security import create_password_reset_token
    from app.integrations.email_provider.email_adapter import MockEmailProvider

    user = (await db.execute(
        select(User).where(func.lower(User.email) == body.email.lower(), User.is_active.is_(True))
    )).scalar_one_or_none()
    if not user:
        return {"message": FORGOT_PASSWORD_MESSAGE}

    token = create_password_reset_token(user.id, user.hashed_password)
    reset_url = f"{settings.frontend_url.rstrip('/')}/reset-password?token={token}"
    await MockEmailProvider().send_email(
        recipient_email=user.email,
        subject="Reset your TalkWiseAI password",
        body=f"Use this link within 30 minutes to choose a new password:\n\n{reset_url}",
        require_approval=False,  # account email, not an AI-drafted message
    )
    db.add(AuditLog(organization_id=user.organization_id, user_id=user.id, action="password_reset_requested"))
    await db.commit()
    logger.info("Password reset requested", user_id=user.id)

    response = {"message": FORGOT_PASSWORD_MESSAGE}
    if settings.is_development and settings.email_provider == "mock":
        response["dev_reset_url"] = reset_url
    return response


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
async def reset_password(body: ResetPasswordRequest, db: AsyncSession = Depends(get_db)):
    """Set a new password using a token from the forgot-password email."""
    from jose import JWTError

    from app.core.security import decode_password_reset_token, reset_token_matches

    invalid = HTTPException(status_code=400, detail="This reset link is invalid or has expired. Request a new one.")
    try:
        payload = decode_password_reset_token(body.token)
    except (JWTError, ValueError):
        raise invalid

    user = await db.get(User, payload.get("sub"))
    if not user or not user.is_active or not reset_token_matches(payload, user.hashed_password):
        raise invalid

    user.hashed_password = hash_password(body.new_password)
    db.add(AuditLog(organization_id=user.organization_id, user_id=user.id, action="password_reset"))
    await db.commit()
