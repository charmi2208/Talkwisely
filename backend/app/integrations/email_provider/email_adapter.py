"""
Email Provider Integration Adapter.

Provides dispatch capabilities for follow-up email drafts.
Includes explicit approval guard preventing unauthorized external emails.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class EmailProvider(ABC):
    """Abstract interface for Email dispatch adapters."""

    @abstractmethod
    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        require_approval: bool = True,
        approved_by_user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        """Dispatch email only when approved."""
        ...


class MockEmailProvider(EmailProvider):
    """Mock Email Provider."""

    async def send_email(
        self,
        recipient_email: str,
        subject: str,
        body: str,
        require_approval: bool = True,
        approved_by_user_id: Optional[str] = None,
    ) -> dict[str, Any]:
        if require_approval and not approved_by_user_id:
            return {
                "status": "pending_user_approval",
                "message": "Email draft generated. Explicit user approval required before dispatch.",
            }

        return {
            "status": "sent",
            "message_id": "msg_email_808",
            "recipient": recipient_email,
            "subject": subject,
            "approved_by": approved_by_user_id,
        }
