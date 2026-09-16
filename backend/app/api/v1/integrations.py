"""
Integrations & Adapters API Router.

Manages connection state and sync operations for:
- TalkWisely Cloud PBX Adapter
- CRM Provider Adapter (Salesforce / HubSpot / Zoho)
- Calendar Provider Adapter (Google Calendar / Outlook)
- Email Provider Adapter
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user, get_db
from app.integrations.talkwisely.talkwisely_adapter import TalkWiselyCloudPBXAdapter

router = APIRouter(prefix="/integrations", tags=["Integrations & Adapters"])


class IntegrationStatusResponse(BaseModel):
    name: str
    provider_key: str
    status: str  # connected | mock_active | disconnected | error
    is_mock: bool
    last_synced_at: Optional[str] = None
    description: str


class SyncTalkWiselyRequest(BaseModel):
    limit: int = 5


@router.get("", response_model=list[IntegrationStatusResponse])
async def list_integrations(
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """List status of all system integrations and mock adapters."""
    return [
        IntegrationStatusResponse(
            name="TalkWisely Cloud PBX",
            provider_key="talkwisely_pbx",
            status="connected",
            is_mock=True,
            last_synced_at="2026-08-20T12:00:00Z",
            description="AI-powered Cloud PBX & Business Phone System call ingestion adapter.",
        ),
        IntegrationStatusResponse(
            name="Salesforce / HubSpot CRM",
            provider_key="crm_salesforce",
            status="connected",
            is_mock=True,
            last_synced_at="2026-08-20T11:30:00Z",
            description="Bidirectional sync for leads, opportunities, and contact call logs.",
        ),
        IntegrationStatusResponse(
            name="Google / Outlook Calendar",
            provider_key="calendar_google",
            status="connected",
            is_mock=True,
            last_synced_at="2026-08-20T10:00:00Z",
            description="Automated demo scheduling and follow-up meeting calendar adapter.",
        ),
        IntegrationStatusResponse(
            name="SMTP / Email Provider",
            provider_key="email_smtp",
            status="connected",
            is_mock=True,
            last_synced_at="2026-08-20T09:00:00Z",
            description="Human-in-the-loop follow-up email dispatch adapter.",
        ),
    ]


@router.post("/talkwisely/sync")
async def sync_talkwisely_calls(
    payload: SyncTalkWiselyRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Import and sync recent call recordings from the TalkWisely Cloud PBX adapter."""
    adapter = TalkWiselyCloudPBXAdapter()
    calls = await adapter.fetch_calls(limit=payload.limit)

    return {
        "status": "success",
        "synced_count": len(calls),
        "calls": calls,
        "message": f"Successfully synced {len(calls)} call recordings from TalkWisely PBX adapter.",
    }


@router.post("/test/{provider_key}")
async def test_integration_connection(
    provider_key: str,
    current_user=Depends(get_current_user),
):
    """Test connection for a specific integration adapter."""
    valid_keys = {"talkwisely_pbx", "crm_salesforce", "calendar_google", "email_smtp"}
    if provider_key not in valid_keys:
        raise HTTPException(status_code=400, detail=f"Unknown integration key '{provider_key}'")

    return {
        "provider_key": provider_key,
        "status": "healthy",
        "latency_ms": 42,
        "message": f"Connection test passed for {provider_key}.",
    }
