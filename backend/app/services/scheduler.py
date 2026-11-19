"""
Background schedule run inside the API process.

- TalkWisely PBX auto-sync: every ``PBX_AUTO_SYNC_INTERVAL_MINUTES``, organizations with
  at least one active member who turned on the ``pbx_auto_sync`` preference get new
  PBX calls imported (as that member) and queued for analysis.
"""

import asyncio

from sqlalchemy import select

from app.core.config import settings
from app.core.logging import get_logger
from app.core.preferences import effective_preferences

logger = get_logger("services.scheduler")


async def run_pbx_auto_sync_once() -> int:
    """One sync pass. Returns how many calls were imported."""
    from app.db.models import User
    from app.db.session import AsyncSessionLocal
    from app.services.pbx_import import ImportBlocked, import_pbx_calls

    imported = 0
    async with AsyncSessionLocal() as db:
        users = (await db.execute(select(User).where(User.is_active.is_(True)).order_by(User.created_at))).scalars().all()
        syncing: dict[str, str] = {}
        for user in users:
            if effective_preferences(user.preferences)["pbx_auto_sync"]:
                syncing.setdefault(user.organization_id, user.id)

        for organization_id, user_id in syncing.items():
            try:
                result = await import_pbx_calls(db, organization_id, user_id)
                imported += result["imported"]
            except ImportBlocked as e:
                logger.info("PBX auto-sync skipped", organization_id=organization_id, reason=str(e))
                await db.rollback()
            except Exception as e:
                logger.error("PBX auto-sync failed", organization_id=organization_id, error=str(e))
                await db.rollback()
    return imported


async def pbx_auto_sync_loop() -> None:
    interval = max(1, settings.pbx_auto_sync_interval_minutes) * 60
    while True:
        await asyncio.sleep(interval)
        try:
            await run_pbx_auto_sync_once()
        except Exception as e:  # keep the loop alive
            logger.error("PBX auto-sync pass failed", error=str(e))
