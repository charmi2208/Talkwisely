"""
Integrations & Adapters API Router.

GET  /api/v1/integrations                 — Each integration's provider, settings and status
PUT  /api/v1/integrations/{key}           — Turn on/off, choose provider, edit settings (admin)
POST /api/v1/integrations/{key}/test      — Run the adapter's health check (admin, manager)
POST /api/v1/integrations/talkwisely/sync — Import new PBX calls as conversations (admin, manager)

Keys: talkwisely, crm, calendar, email. Only mock providers are implemented; the
response says so (``is_mock``) instead of claiming a live connection.
"""

from typing import Any, Optional

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db, require_roles
from app.db.models import AuditLog
from app.integrations.registry import INTEGRATIONS, check_connection, clean_config, get_integration
from app.services.pbx_import import ImportBlocked, import_pbx_calls

router = APIRouter(prefix="/integrations", tags=["Integrations & Adapters"])


class ProviderOptionResponse(BaseModel):
    key: str
    label: str
    available: bool
    note: str


class ConfigFieldResponse(BaseModel):
    key: str
    label: str
    type: str
    description: str
    min: Optional[int] = None
    max: Optional[int] = None


class IntegrationResponse(BaseModel):
    key: str
    name: str
    description: str
    provider: str
    provider_label: str
    is_enabled: bool
    is_mock: bool
    status: str  # mock_active | disabled
    config: dict[str, Any]
    config_fields: list[ConfigFieldResponse]
    providers: list[ProviderOptionResponse]
    last_synced_at: Optional[str] = None


class UpdateIntegrationRequest(BaseModel):
    is_enabled: Optional[bool] = None
    provider: Optional[str] = None
    config: Optional[dict[str, Any]] = None


def _spec_or_404(key: str):
    spec = INTEGRATIONS.get(key)
    if not spec:
        raise HTTPException(status_code=404, detail=f"Unknown integration '{key}'")
    return spec


def _to_response(spec, row) -> IntegrationResponse:
    provider = next((p for p in spec.providers if p.key == row.provider), spec.providers[0])
    return IntegrationResponse(
        key=spec.key,
        name=spec.name,
        description=spec.description,
        provider=provider.key,
        provider_label=provider.label,
        is_enabled=row.is_enabled,
        is_mock=provider.key == "mock",
        status="disabled" if not row.is_enabled else "mock_active",
        config=row.config or {},
        config_fields=[
            ConfigFieldResponse(key=f.key, label=f.label, type=f.type, description=f.description, min=f.min, max=f.max)
            for f in spec.config_fields
        ],
        providers=[ProviderOptionResponse(key=p.key, label=p.label, available=p.available, note=p.note) for p in spec.providers],
        last_synced_at=row.last_synced_at.isoformat() if row.last_synced_at else None,
    )


@router.get("", response_model=list[IntegrationResponse])
async def list_integrations(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Every integration with its provider, settings and status for this organization."""
    rows = [(spec, await get_integration(db, current_user.organization_id, key)) for key, spec in INTEGRATIONS.items()]
    await db.commit()  # persists rows created with defaults on first visit
    return [_to_response(spec, row) for spec, row in rows]


@router.put("/{key}", response_model=IntegrationResponse)
async def update_integration(
    key: str,
    payload: UpdateIntegrationRequest,
    current_user=Depends(require_roles("admin")),
    db: AsyncSession = Depends(get_db),
):
    """Turn an integration on or off, pick its provider or edit its settings (admin only)."""
    spec = _spec_or_404(key)
    row = await get_integration(db, current_user.organization_id, key)

    if payload.provider is not None:
        option = next((p for p in spec.providers if p.key == payload.provider), None)
        if not option:
            raise HTTPException(status_code=400, detail=f"Unknown provider '{payload.provider}'")
        if not option.available:
            raise HTTPException(status_code=400, detail=f"{option.label}: {option.note}")
        row.provider = option.key
    if payload.config is not None:
        try:
            row.config = clean_config(spec, {**(row.config or {}), **payload.config})
        except ValueError as e:
            raise HTTPException(status_code=422, detail=str(e))
    if payload.is_enabled is not None:
        row.is_enabled = payload.is_enabled
        row.is_connected = payload.is_enabled

    db.add(AuditLog(
        organization_id=current_user.organization_id,
        user_id=current_user.id,
        action="integration_update",
        resource_type="integration",
        resource_id=row.id,
        details={"key": key, **payload.model_dump(exclude_none=True)},
    ))
    await db.commit()
    return _to_response(spec, row)


@router.post("/talkwisely/sync")
async def sync_talkwisely_calls(
    background_tasks: BackgroundTasks,
    current_user=Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Import new calls from the TalkWisely PBX adapter and queue them for analysis."""
    try:
        result = await import_pbx_calls(db, current_user.organization_id, current_user.id, background_tasks)
    except ImportBlocked as e:
        raise HTTPException(status_code=409, detail=str(e))
    imported, skipped = result["imported"], result["skipped"]
    message = (
        f"Imported {imported} new call{'s' if imported != 1 else ''}; analysis has started."
        if imported else "No new calls to import."
    )
    if skipped:
        message += f" Skipped {skipped} already imported."
    return {**result, "message": message}


@router.post("/{key}/test")
async def test_integration_connection(
    key: str,
    current_user=Depends(require_roles("admin", "manager")),
    db: AsyncSession = Depends(get_db),
):
    """Run the configured adapter's health check and report how long it took."""
    _spec_or_404(key)
    row = await get_integration(db, current_user.organization_id, key)
    await db.commit()
    if not row.is_enabled:
        return {"key": key, "ok": False, "latency_ms": None, "message": "This integration is turned off."}
    result = await check_connection(key, row.provider)
    return {"key": key, **result}
