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


class MockCalendarProvider(CalendarProvider):
    """Mock Calendar Provider for local demo."""

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
