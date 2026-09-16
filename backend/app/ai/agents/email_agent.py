"""
Email Generation Agent (Agent 12).

Generates context-aware follow-up email drafts based strictly on conversation intelligence.
"""

from typing import Any, Optional
from app.ai.providers.base import LLMMessage, LLMProvider
from app.core.logging import get_logger

logger = get_logger("ai.agents.email")


class EmailGenerationAgent:
    """Agent for drafting follow-up emails."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate_email(
        self,
        conversation_title: str,
        summary: Optional[dict] = None,
        action_items: Optional[list[dict]] = None,
        sales_insight: Optional[dict] = None,
        email_type: str = "thank_you",  # thank_you | meeting_summary | proposal_follow_up | demo_follow_up
        tone: str = "professional",     # professional | friendly | concise | formal
        recipient_name: Optional[str] = None,
        sender_name: Optional[str] = None,
    ) -> dict[str, Any]:
        """
        Generate a personalized follow-up email based on conversation details.
        """
        exec_summary = summary.get("executive_summary", "") if summary else ""
        next_steps = summary.get("next_steps", []) if summary else []
        tasks = [a.get("description", "") for a in (action_items or []) if a.get("description")]

        system_prompt = (
            "You are a sales & customer communication AI specialist. "
            "Draft a context-aware follow-up email based strictly on conversation facts. "
            "Never invent pricing, features, or deadlines not mentioned. "
            "Return JSON with: subject (string), body (markdown text), suggested_actions (list of strings)."
        )

        user_content = (
            f"Conversation Title: {conversation_title}\n"
            f"Email Type: {email_type}\n"
            f"Desired Tone: {tone}\n"
            f"Recipient: {recipient_name or 'Valued Client'}\n"
            f"Sender: {sender_name or 'Sales Representative'}\n"
            f"Executive Summary: {exec_summary}\n"
            f"Next Steps: {', '.join(next_steps)}\n"
            f"Action Items: {', '.join(tasks[:3])}\n"
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_content),
        ]

        try:
            result = await self.llm.complete_json(messages)
            return {
                "subject": result.get("subject", f"Follow-up: {conversation_title}"),
                "body": result.get("body", f"Thank you for our recent call regarding {conversation_title}."),
                "suggested_actions": result.get("suggested_actions", []),
                "email_type": email_type,
                "tone": tone,
            }
        except Exception as e:
            logger.error("Email generation failed", error=str(e))
            return {
                "subject": f"Follow-up: {conversation_title}",
                "body": (
                    f"Hi {recipient_name or 'there'},\n\n"
                    f"Thank you for taking the time to speak today regarding {conversation_title}.\n\n"
                    f"Summary of discussion: {exec_summary or 'We reviewed your requirements and next steps.'}\n\n"
                    f"Best regards,\n{sender_name or 'The Team'}"
                ),
                "suggested_actions": next_steps[:2] if next_steps else ["Send follow-up proposal"],
                "email_type": email_type,
                "tone": tone,
            }
