"""
Import calls from the TalkWisely PBX adapter as conversations.

Used by ``POST /integrations/talkwisely/sync`` and by the scheduled auto-sync
(``pbx_auto_sync`` user preference, see app/main.py).
"""

import os
import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.logging import get_logger
from app.db.models import AuditLog, Conversation, ProcessingJob
from app.integrations.registry import get_integration, mark_synced
from app.integrations.talkwisely.talkwisely_adapter import TalkWiselyCloudPBXAdapter

logger = get_logger("services.pbx_import")


class ImportBlocked(Exception):
    """The import can't run right now; the message explains why and is shown to users."""


def _file_name(call_id: str) -> str:
    return f"talkwisely-{call_id}.opus"


def _parse_timestamp(value: str | None) -> datetime:
    try:
        return datetime.fromisoformat((value or "").replace("Z", "+00:00")).replace(tzinfo=None)
    except ValueError:
        return datetime.utcnow()


async def import_pbx_calls(db: AsyncSession, organization_id: str, user_id: str, background_tasks=None) -> dict:
    """Fetch recent PBX calls, create conversations for new ones and queue their analysis."""
    integration = await get_integration(db, organization_id, "talkwisely")
    if not integration.is_enabled:
        raise ImportBlocked("The TalkWisely integration is turned off. Turn it on under Integrations.")
    if settings.stt_provider != "mock":
        raise ImportBlocked(
            "The TalkWisely adapter is a mock that has no real recordings, so imported calls can only be "
            "analyzed with STT_PROVIDER=mock. Upload recordings directly instead."
        )

    adapter = TalkWiselyCloudPBXAdapter()
    calls = await adapter.fetch_calls(limit=int((integration.config or {}).get("import_limit", 5)))
    names = [_file_name(c["call_id"]) for c in calls]
    already = set((await db.execute(
        select(Conversation.file_name).where(
            Conversation.organization_id == organization_id, Conversation.file_name.in_(names)
        )
    )).scalars().all())

    upload_dir = os.path.join(settings.storage_local_path, "uploads", organization_id)
    os.makedirs(upload_dir, exist_ok=True)
    queued: list[tuple[str, str, str]] = []
    for call in calls:
        name = _file_name(call["call_id"])
        if name in already:
            continue
        audio = await adapter.fetch_call_recording(call["call_id"])
        file_path = os.path.join(upload_dir, f"{uuid.uuid4()}.opus")
        with open(file_path, "wb") as f:
            f.write(audio)

        conv_id, job_id = str(uuid.uuid4()), str(uuid.uuid4())
        db.add(Conversation(
            id=conv_id,
            organization_id=organization_id,
            created_by=user_id,
            title=f"TalkWisely call with {call.get('caller_id', 'unknown caller')}",
            status="uploaded",
            duration_seconds=call.get("duration_seconds"),
            file_path=file_path,
            file_name=name,
            file_size_bytes=len(audio),
            file_type="audio",
            occurred_at=_parse_timestamp(call.get("timestamp")),
            extra_metadata={
                "source": "talkwisely_pbx",
                "mock": True,
                "call_id": call["call_id"],
                "caller_id": call.get("caller_id"),
                "pbx_agent_name": call.get("agent_name"),
                "call_type": call.get("call_type"),
            },
        ))
        db.add(ProcessingJob(
            id=job_id, conversation_id=conv_id, job_type="pbx_import",
            status="queued", progress=0, current_step="Queued",
        ))
        queued.append((conv_id, job_id, file_path))

    mark_synced(integration)
    db.add(AuditLog(
        id=str(uuid.uuid4()),
        organization_id=organization_id,
        user_id=user_id,
        action="pbx_sync",
        resource_type="integration",
        resource_id=integration.id,
        details={"imported": len(queued), "skipped": len(calls) - len(queued)},
    ))
    await db.commit()

    from app.workers.conversation_tasks import enqueue_conversation_processing

    for conv_id, job_id, file_path in queued:
        enqueue_conversation_processing(background_tasks, conv_id, job_id, file_path)

    logger.info("PBX calls imported", organization_id=organization_id, imported=len(queued))
    return {
        "imported": len(queued),
        "skipped": len(calls) - len(queued),
        "conversation_ids": [c for c, _, _ in queued],
    }
