"""
System & Administration API Router.

GET /api/v1/system/ai-settings  — Which AI providers and models are configured (admin, manager)
GET /api/v1/system/audit-logs   — Recent audit trail for the organization (admin)

AI providers are configured through environment variables (see backend/.env.local.example)
so secrets never pass through the API; this endpoint only reports what's active.
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.dependencies import get_db, require_roles
from app.db.models import AuditLog, User

router = APIRouter(prefix="/system", tags=["System & Administration"])


class AuditLogItem(BaseModel):
    id: str
    action: str
    user_name: Optional[str] = None
    resource_type: Optional[str] = None
    resource_id: Optional[str] = None
    details: dict = {}
    ip_address: Optional[str] = None
    created_at: str


@router.get("/ai-settings")
async def get_ai_settings(current_user=Depends(require_roles("admin", "manager"))):
    """Active providers and models. Secrets are never included."""
    def provider(kind: str, name: str, model: str | None, note: str) -> dict:
        return {"kind": kind, "provider": name, "model": model, "is_mock": name == "mock", "note": note}

    return {
        "providers": [
            provider("Language model", settings.llm_provider,
                     settings.llm_model if settings.llm_provider != "mock" else None,
                     "Runs the analysis agents, Copilot, emails and reports"),
            provider("Speech-to-text", settings.stt_provider,
                     settings.stt_api_model if settings.stt_provider == "whisper_api"
                     else settings.whisper_model if settings.stt_provider == "whisper_local" else None,
                     "Transcribes uploaded recordings"),
            provider("Embeddings", settings.embedding_provider,
                     settings.embedding_model if settings.embedding_provider == "openai"
                     else "all-MiniLM-L6-v2" if settings.embedding_provider == "local" else None,
                     "Powers semantic search and the Copilot"),
        ],
        "task_queue": settings.task_queue,
        "llm_api_key_configured": bool(settings.llm_api_key),
        "how_to_change": "Set LLM_PROVIDER, STT_PROVIDER and EMBEDDING_PROVIDER in backend/.env.local, then restart the API.",
    }


@router.get("/audit-logs", response_model=list[AuditLogItem])
async def list_audit_logs(
    action: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=200),
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Most recent audit events (logins, uploads, deletions, approvals, setting changes)."""
    query = (
        select(AuditLog, User.full_name)
        .join(User, AuditLog.user_id == User.id, isouter=True)
        .where(AuditLog.organization_id == current_user.organization_id)
    )
    if action:
        query = query.where(AuditLog.action == action)
    rows = (await db.execute(query.order_by(AuditLog.created_at.desc()).limit(limit))).all()
    return [
        AuditLogItem(
            id=log.id,
            action=log.action,
            user_name=name,
            resource_type=log.resource_type,
            resource_id=log.resource_id,
            details=log.details or {},
            ip_address=log.ip_address,
            created_at=log.created_at.isoformat(),
        )
        for log, name in rows
    ]
