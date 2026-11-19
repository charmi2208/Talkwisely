"""
Meeting platform adapters (docs/SPEC.md §6D: Zoom, Google Meet, Microsoft Teams).

Each platform will get an implementation of ``MeetingProviderAdapter`` that lists cloud
recordings and downloads them. Only the mock exists: the platforms' APIs need OAuth apps
this project doesn't have, and the spec rule is to never invent third-party APIs.
"""

from abc import ABC, abstractmethod
from typing import Any


class MeetingProviderAdapter(ABC):
    """Lists and downloads recorded meetings from a video meeting platform."""

    @abstractmethod
    async def list_recordings(self, limit: int = 10) -> list[dict[str, Any]]:
        """Recent recordings: recording_id, platform, topic, host, start_time, duration_seconds, participants."""

    @abstractmethod
    async def download_recording(self, recording_id: str) -> bytes:
        """Audio (or video) of one recording."""

    async def health_check(self) -> dict[str, Any]:
        """Check the adapter can reach its platform. Returns {"ok": bool, "message": str}."""
        return {"ok": False, "message": "Health check not implemented for this adapter."}


class MockMeetingAdapter(MeetingProviderAdapter):
    """Mock meeting platform: two sample recordings with placeholder audio.

    Imported meetings can only be analyzed with the mock speech-to-text provider,
    which ignores the audio.
    """

    is_mock = True

    async def list_recordings(self, limit: int = 10) -> list[dict[str, Any]]:
        return [
            {
                "recording_id": "zoom_rec_301",
                "platform": "zoom",
                "topic": "Quarterly business review with Northwind",
                "host": "Priya Sharma",
                "start_time": "2026-11-18T10:00:00Z",
                "duration_seconds": 1860,
                "participants": 5,
            },
            {
                "recording_id": "teams_rec_302",
                "platform": "teams",
                "topic": "Weekly support stand-up",
                "host": "Alex Thompson",
                "start_time": "2026-11-19T09:30:00Z",
                "duration_seconds": 900,
                "participants": 7,
            },
        ][:limit]

    async def download_recording(self, recording_id: str) -> bytes:
        return b"MOCK_MEETING_RECORDING"

    async def health_check(self) -> dict[str, Any]:
        return {"ok": True, "message": "Mock meeting adapter responded with sample recordings. No meeting platform was contacted."}
