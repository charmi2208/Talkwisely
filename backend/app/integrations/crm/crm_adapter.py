"""
CRM Provider Adapter Abstraction.

Provides clean interfaces for connecting TalkWiseAI to external CRMs
(Salesforce, HubSpot, Zoho).
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class CRMProvider(ABC):
    """Abstract interface for CRM integration adapters."""

    @abstractmethod
    async def update_lead(self, lead_id: str, fields: dict[str, Any]) -> bool:
        """Update fields on a CRM lead entity."""
        ...

    @abstractmethod
    async def update_opportunity(self, opportunity_id: str, fields: dict[str, Any]) -> bool:
        """Update fields on a CRM opportunity/deal entity."""
        ...

    @abstractmethod
    async def log_call(self, contact_id: str, call_summary: str, duration: int) -> bool:
        """Log a call activity entry to a contact's activity feed."""
        ...

    async def health_check(self) -> dict[str, Any]:
        """Check the adapter can reach its service. Returns {"ok": bool, "message": str}."""
        return {"ok": False, "message": "Health check not implemented for this adapter."}

    @property
    @abstractmethod
    def provider_name(self) -> str:
        ...


class MockCRMProvider(CRMProvider):
    """Mock CRM provider simulating Salesforce/HubSpot API sync."""

    async def health_check(self) -> dict[str, Any]:
        return {"ok": True, "message": "Mock CRM adapter responded. No external CRM was contacted."}

    def __init__(self, crm_name: str = "Salesforce"):
        self._name = crm_name

    async def update_lead(self, lead_id: str, fields: dict[str, Any]) -> bool:
        # Simulates successful CRM write
        return True

    async def update_opportunity(self, opportunity_id: str, fields: dict[str, Any]) -> bool:
        return True

    async def log_call(self, contact_id: str, call_summary: str, duration: int) -> bool:
        return True

    @property
    def provider_name(self) -> str:
        return self._name
