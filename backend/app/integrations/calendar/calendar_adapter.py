"""
Calendar Provider Integration Adapter.

Provides calendar scheduling capabilities (Google Calendar, Outlook).
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CalendarProvider(ABC):
    """Abstract interface for Calendar adapters."""

    @abstractmethod
    async def schedule_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        attendees: list[str],
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        """Schedule a new calendar event."""
        ...

    async def health_check(self) -> dict[str, Any]:
        """Check the adapter can reach its service. Returns {"ok": bool, "message": str}."""
        return {"ok": False, "message": "Health check not implemented for this adapter."}


class MockCalendarProvider(CalendarProvider):
    """Mock Calendar Provider for local demo."""

    async def health_check(self) -> dict[str, Any]:
        return {"ok": True, "message": "Mock calendar adapter responded. No calendar was contacted."}

    async def schedule_event(
        self,
        title: str,
        start_time: str,
        end_time: str,
        attendees: list[str],
        description: Optional[str] = None,
    ) -> dict[str, Any]:
        return {
            "event_id": "cal_evt_101",
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "attendees": attendees,
            "meeting_link": "https://meet.talkwisely.com/demo-room-101",
            "status": "confirmed",
        }
