"""
FastAPI Dependency Injection.

Provides reusable dependencies for authentication, database access,
provider resolution, and RBAC enforcement.
"""

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_access_token
from app.db.session import get_db

bearer_scheme = HTTPBearer()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> str:
    """Extract and validate the user ID from the Authorization Bearer token."""
    token = credentials.credentials
    try:
        payload = decode_access_token(token)
        user_id: str | None = payload.get("sub")
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication token",
            )
        return user_id
    except (JWTError, ValueError):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired authentication token",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_user(
    user_id: str = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db),
):
    """Load the full User object from the database."""
    from sqlalchemy import select
    from app.db.models import User

    result = await db.execute(select(User).where(User.id == user_id, User.is_active == True))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found or inactive",
        )
    return user


def require_roles(*allowed_roles: str):
    """
    Dependency factory that enforces RBAC.

    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user=Depends(require_roles("admin"))):
            ...
    """
    async def _check_roles(
        user=Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
    ):
        from sqlalchemy import select
        from sqlalchemy.orm import selectinload
        from app.db.models import User, UserRole, Role

        # Load user with roles
        result = await db.execute(
            select(User)
            .options(selectinload(User.user_roles).selectinload(UserRole.role))
            .where(User.id == user.id)
        )
        user_with_roles = result.scalar_one_or_none()

        if not user_with_roles:
            raise HTTPException(status_code=403, detail="Access denied")

        user_role_names = {ur.role.name for ur in user_with_roles.user_roles}

        if not any(role in user_role_names for role in allowed_roles):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This action requires one of these roles: {', '.join(allowed_roles)}",
            )

        return user_with_roles

    return _check_roles
