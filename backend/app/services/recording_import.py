"""
Import recordings from external systems as conversations.

- TalkWisely PBX calls: ``POST /integrations/talkwisely/sync`` and the scheduled auto-sync
  (``pbx_auto_sync`` user preference, see app/services/scheduler.py).
- Meeting platform recordings (Zoom, Google Meet, Teams): ``POST /integrations/meetings/sync``.

Both share ``_import_recordings``: skip what was already imported, save each recording,
create a conversation and processing job, then queue the analysis like an upload.
"""

import os
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import AuditLog, Conversation, ProcessingJob
from app.integrations.meetings.meeting_adapter import MockMeetingAdapter
from app.integrations.registry import INTEGRATIONS, get_integration, mark_synced
from app.integrations.talkwisely.talkwisely_adapter import TalkWiselyCloudPBXAdapter

logger = get_logger("services.recording_import")

PLATFORM_LABELS = {"zoom": "Zoom", "google_meet": "Google Meet", "teams": "Teams"}


class ImportBlocked(Exception):
    """The import can't run right now; the message explains why and is shown to users."""


@dataclass
class ImportedRecording:
    """What the generic importer needs to know about one external recording."""
    external_id: str
    file_name: str          # stable per recording; used to skip duplicates
    extension: str
    title: str
    duration_seconds: int | None
    occurred_at: datetime
    metadata: dict[str, Any]
    fetch_audio: Callable[[], Awaitable[bytes]]


def _parse_timestamp(value: str | None) -> datetime:
    try:
        return datetime.fromisoformat((value or "").replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.utcnow()


async def _import_recordings(
    db: AsyncSession,
    organization_id: str,
    user_id: str,
    integration_key: str,
    load: Callable[[int], Awaitable[list[ImportedRecording]]],
    job_type: str,
    background_tasks=None,
) -> dict:
    integration = await get_integration(db, organization_id, integration_key)
    name = INTEGRATIONS[integration_key].name
    if not integration.is_enabled:
        raise ImportBlocked(f"The {name} integration is turned off. Turn it on under Integrations.")
    if settings.stt_provider != "mock":
        raise ImportBlocked(
            f"The {name} adapter is a mock that has no real recordings, so imports can only be "
            "analyzed with STT_PROVIDER=mock. Upload recordings directly instead."
        )

    recordings = await load(int((integration.config or {}).get("import_limit", 5)))
    already = set((await db.execute(
        select(Conversation.file_name).where(
            Conversation.organization_id == organization_id,
            Conversation.file_name.in_([r.file_name for r in recordings]),
        )
    )).scalars().all())

    upload_dir = os.path.join(settings.storage_local_path, "uploads", organization_id)
    os.makedirs(upload_dir, exist_ok=True)
    queued: list[tuple[str, str, str]] = []
    for rec in recordings:
        if rec.file_name in already:
            continue
        audio = await rec.fetch_audio()
        file_path = os.path.join(upload_dir, f"{uuid.uuid4()}{rec.extension}")
        with open(file_path, "wb") as f:
            f.write(audio)

        conv_id, job_id = str(uuid.uuid4()), str(uuid.uuid4())
        db.add(Conversation(
            id=conv_id,
            organization_id=organization_id,
            created_by=user_id,
            title=rec.title,
            status="uploaded",
            duration_seconds=rec.duration_seconds,
            file_path=file_path,
            file_name=rec.file_name,
            file_size_bytes=len(audio),
            file_type="audio",
            occurred_at=rec.occurred_at,
            extra_metadata={"mock": True, **rec.metadata},
        ))
        db.add(ProcessingJob(
            id=job_id, conversation_id=conv_id, job_type=job_type,
            status="queued", progress=0, current_step="Queued",
        ))
        queued.append((conv_id, job_id, file_path))

    mark_synced(integration)
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        user_id=user_id,
        action="pbx_sync" if integration_key == "talkwisely" else f"{integration_key}_sync",
        resource_type="integration",
        resource_id=integration.id,
        details={"imported": len(queued), "skipped": len(recordings) - len(queued)},
    ))
    await db.commit()

    from app.workers.conversation_tasks import enqueue_conversation_processing

    for conv_id, job_id, file_path in queued:
        enqueue_conversation_processing(background_tasks, conv_id, job_id, file_path)

    logger.info("Recordings imported", integration=integration_key, organization_id=organization_id, imported=len(queued))
    return {
        "imported": len(queued),
        "skipped": len(recordings) - len(queued),
        "conversation_ids": [c for c, _, _ in queued],
    }


async def import_pbx_calls(db: AsyncSession, organization_id: str, user_id: str, background_tasks=None) -> dict:
    """Fetch recent PBX calls, create conversations for new ones and queue their analysis."""
    adapter = TalkWiselyCloudPBXAdapter()

    async def load(limit: int) -> list[ImportedRecording]:
        calls = await adapter.fetch_calls(limit=limit)
        return [
            ImportedRecording(
                external_id=call["call_id"],
                file_name=f"talkwisely-{call['call_id']}.opus",
                extension=".opus",
                title=f"TalkWisely call with {call.get('caller_id', 'unknown caller')}",
                duration_seconds=call.get("duration_seconds"),
                occurred_at=_parse_timestamp(call.get("timestamp")),
                metadata={
                    "source": "talkwisely_pbx",
                    "call_id": call["call_id"],
                    "caller_id": call.get("caller_id"),
                    "pbx_agent_name": call.get("agent_name"),
                    "call_type": call.get("call_type"),
                },
                fetch_audio=lambda cid=call["call_id"]: adapter.fetch_call_recording(cid),
            )
            for call in calls
        ]

    return await _import_recordings(db, organization_id, user_id, "talkwisely", load, "pbx_import", background_tasks)


async def import_meeting_recordings(db: AsyncSession, organization_id: str, user_id: str, background_tasks=None) -> dict:
    """Fetch recent meeting recordings, create conversations for new ones and queue their analysis."""
    adapter = MockMeetingAdapter()

    async def load(limit: int) -> list[ImportedRecording]:
        recordings = await adapter.list_recordings(limit=limit)
        return [
            ImportedRecording(
                external_id=rec["recording_id"],
                file_name=f"meeting-{rec['recording_id']}.m4a",
                extension=".m4a",
                title=f"{PLATFORM_LABELS.get(rec.get('platform'), 'Meeting')} meeting: {rec.get('topic', 'Untitled')}",
                duration_seconds=rec.get("duration_seconds"),
                occurred_at=_parse_timestamp(rec.get("start_time")),
                metadata={
                    "source": "meeting_platform",
                    "platform": rec.get("platform"),
                    "recording_id": rec["recording_id"],
                    "host": rec.get("host"),
                    "participants": rec.get("participants"),
                },
                fetch_audio=lambda rid=rec["recording_id"]: adapter.download_recording(rid),
            )
            for rec in recordings
        ]

    return await _import_recordings(db, organization_id, user_id, "meetings", load, "meeting_import", background_tasks)
