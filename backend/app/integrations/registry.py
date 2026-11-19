"""
Integration registry: what each adapter is, which providers exist, and its settings.

Only the mock providers are implemented. Real providers are listed so the UI can show
what's planned, but they can't be selected until an adapter exists (docs/SPEC.md:
never invent third-party APIs; ship an adapter interface plus a mock instead).

Secrets (API keys, OAuth client secrets) never live here or in the database; they come
from environment variables. ``Integration.config`` holds only the non-secret settings
declared in ``config_fields``.
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Integration


@dataclass(frozen=True)
class ProviderOption:
    key: str
    label: str
    available: bool
    note: str = ""


@dataclass(frozen=True)
class ConfigField:
    key: str
    label: str
    type: str  # text | number | email
    default: Any
    description: str = ""
    min: int | None = None
    max: int | None = None


@dataclass(frozen=True)
class IntegrationSpec:
    key: str  # also Integration.integration_type
    name: str
    description: str
    providers: list[ProviderOption]
    config_fields: list[ConfigField] = field(default_factory=list)


_NOT_BUILT = "Adapter not implemented yet"

INTEGRATIONS: dict[str, IntegrationSpec] = {
    "talkwisely": IntegrationSpec(
        key="talkwisely",
        name="TalkWisely Cloud PBX",
        description="Imports call recordings and metadata from the TalkWisely business phone system.",
        providers=[
            ProviderOption("mock", "Mock PBX (sample calls)", True, "Returns two sample call records"),
            ProviderOption("talkwisely", "TalkWisely API", False, _NOT_BUILT),
        ],
        config_fields=[
            ConfigField("import_limit", "Calls per sync", "number", 5, "Most calls imported in one sync", 1, 50),
        ],
    ),
    "meetings": IntegrationSpec(
        key="meetings",
        name="Meeting platforms",
        description="Imports recorded meetings from Zoom, Google Meet or Microsoft Teams for analysis.",
        providers=[
            ProviderOption("mock", "Mock meetings (sample recordings)", True, "Returns two sample meeting recordings"),
            ProviderOption("zoom", "Zoom", False, _NOT_BUILT),
            ProviderOption("google_meet", "Google Meet", False, _NOT_BUILT),
            ProviderOption("teams", "Microsoft Teams", False, _NOT_BUILT),
        ],
        config_fields=[
            ConfigField("import_limit", "Recordings per sync", "number", 5, "Most recordings imported in one sync", 1, 50),
        ],
    ),
    "crm": IntegrationSpec(
        key="crm",
        name="CRM",
        description="Writes approved CRM update proposals (lead score, stage, next step) to your CRM.",
        providers=[
            ProviderOption("mock", "Mock CRM", True, "Accepts writes without contacting a real CRM"),
            ProviderOption("hubspot", "HubSpot", False, _NOT_BUILT),
            ProviderOption("salesforce", "Salesforce", False, _NOT_BUILT),
            ProviderOption("zoho", "Zoho CRM", False, _NOT_BUILT),
        ],
        config_fields=[
            ConfigField("crm_name", "CRM display name", "text", "Salesforce", "Shown on approved proposals"),
        ],
    ),
    "calendar": IntegrationSpec(
        key="calendar",
        name="Calendar",
        description="Schedules follow-up meetings and demos from recommended next steps.",
        providers=[
            ProviderOption("mock", "Mock calendar", True, "Returns a confirmed event without booking anything"),
            ProviderOption("google", "Google Calendar", False, _NOT_BUILT),
            ProviderOption("outlook", "Outlook", False, _NOT_BUILT),
        ],
        config_fields=[
            ConfigField("default_duration_minutes", "Default meeting length (minutes)", "number", 30, "", 15, 240),
        ],
    ),
    "email": IntegrationSpec(
        key="email",
        name="Email",
        description="Sends follow-up emails, only after a person reviews and approves each one.",
        providers=[
            ProviderOption("mock", "Mock email", True, "Reports success without sending anything"),
            ProviderOption("smtp", "SMTP", False, _NOT_BUILT),
            ProviderOption("sendgrid", "SendGrid", False, _NOT_BUILT),
        ],
        config_fields=[
            ConfigField("from_address", "Send from", "email", "noreply@talkwiseai.com", "Sender address on outgoing email"),
        ],
    ),
}


def default_config(spec: IntegrationSpec) -> dict[str, Any]:
    return {f.key: f.default for f in spec.config_fields}


def clean_config(spec: IntegrationSpec, config: dict[str, Any]) -> dict[str, Any]:
    """Keep declared fields only, coerced to their type and bounds. Raises ValueError."""
    cleaned = default_config(spec)
    for f in spec.config_fields:
        if f.key not in config or config[f.key] in (None, ""):
            continue
        value = config[f.key]
        if f.type == "number":
            try:
                value = int(value)
            except (TypeError, ValueError):
                raise ValueError(f"{f.label} must be a whole number")
            if f.min is not None and value < f.min or f.max is not None and value > f.max:
                raise ValueError(f"{f.label} must be between {f.min} and {f.max}")
        else:
            value = str(value).strip()[:255]
            if f.type == "email" and "@" not in value:
                raise ValueError(f"{f.label} must be an email address")
        cleaned[f.key] = value
    return cleaned


async def get_integration(db: AsyncSession, organization_id: str, key: str) -> Integration:
    """The organization's row for an integration, created with mock defaults on first use."""
    spec = INTEGRATIONS[key]
    row = (await db.execute(
        select(Integration).where(Integration.organization_id == organization_id, Integration.integration_type == key)
    )).scalars().first()
    if row is None:
        row = Integration(
            organization_id=organization_id,
            integration_type=key,
            provider="mock",
            is_enabled=True,
            is_connected=True,
            config=default_config(spec),
        )
        db.add(row)
        await db.flush()
    else:
        # Rows seeded before config fields existed hold other keys; normalize them
        try:
            normalized = clean_config(spec, row.config or {})
        except ValueError:
            normalized = default_config(spec)
        if normalized != row.config:
            row.config = normalized
    return row


async def check_connection(key: str, provider: str) -> dict[str, Any]:
    """Call the adapter's health check and time it."""
    from app.integrations.calendar.calendar_adapter import MockCalendarProvider
    from app.integrations.crm.crm_adapter import MockCRMProvider
    from app.integrations.email_provider.email_adapter import MockEmailProvider
    from app.integrations.meetings.meeting_adapter import MockMeetingAdapter
    from app.integrations.talkwisely.talkwisely_adapter import TalkWiselyCloudPBXAdapter

    adapters = {
        "talkwisely": TalkWiselyCloudPBXAdapter,
        "meetings": MockMeetingAdapter,
        "crm": MockCRMProvider,
        "calendar": MockCalendarProvider,
        "email": MockEmailProvider,
    }
    if provider != "mock":
        return {"ok": False, "latency_ms": None, "message": f"The {provider} adapter isn't implemented yet."}
    started = time.perf_counter()
    result = await adapters[key]().health_check()
    latency = round((time.perf_counter() - started) * 1000, 1)
    return {"ok": bool(result.get("ok")), "latency_ms": latency, "message": result.get("message", "")}


def mark_synced(row: Integration) -> None:
    row.last_synced_at = datetime.utcnow()
