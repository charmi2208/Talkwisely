"""
TalkWisely Cloud PBX Integration Adapter.

Provides the abstraction layer for syncing call recordings and metadata
from TalkWisely Cloud PBX / Business Phone System.
"""

from abc import ABC, abstractmethod
from typing import Any


class CallProviderAdapter(ABC):
    """Abstract adapter interface for VoIP / PBX Call Provider systems."""

    @abstractmethod
    async def fetch_calls(self, limit: int = 10) -> list[dict[str, Any]]:
        """Fetch list of call records from PBX service."""
        ...

    @abstractmethod
    async def fetch_call_recording(self, call_id: str) -> bytes:
        """Download call recording audio stream."""
        ...

    @abstractmethod
    async def fetch_call_metadata(self, call_id: str) -> dict[str, Any]:
        """Fetch metadata (caller_id, duration, agent_id, timestamp)."""
        ...


class TalkWiselyCloudPBXAdapter(CallProviderAdapter):
    """TalkWisely Cloud PBX Call Provider implementation."""

    async def fetch_calls(self, limit: int = 10) -> list[dict[str, Any]]:
        """Return mock/simulated call records from TalkWisely PBX."""
        return [
            {
                "call_id": "tw_call_901",
                "caller_id": "+44 20 7946 0912",
                "agent_name": "Sarah Jenkins",
                "duration_seconds": 415,
                "call_type": "inbound_sales",
                "timestamp": "2026-08-20T14:30:00Z",
                "status": "ready_for_ai_processing",
            },
            {
                "call_id": "tw_call_902",
                "caller_id": "+1 415 555 2671",
                "agent_name": "Michael Chang",
                "duration_seconds": 290,
                "call_type": "demo_call",
                "timestamp": "2026-08-20T15:15:00Z",
                "status": "ready_for_ai_processing",
            },
        ][:limit]

    async def fetch_call_recording(self, call_id: str) -> bytes:
        # Returns empty audio bytes indicator for mock recording stream
        return b"MOCK_TALKWISELY_PBX_AUDIO_STREAM"

    async def fetch_call_metadata(self, call_id: str) -> dict[str, Any]:
        return {
            "call_id": call_id,
            "provider": "TalkWisely Cloud PBX",
            "codec": "opus",
            "sample_rate": 16000,
        }
