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
            "Never invent pricing, features, names or deadlines not mentioned. "
            "If the recipient's name is unknown, use a neutral greeting such as 'Hi there'. "
            "If the sender's name is unknown, sign off with '[Your name]' so the user fills it in. "
            "Return JSON with: subject (string), body (plain-text email with line breaks, no markdown), "
            "suggested_actions (list of strings)."
        )

        user_content = (
            f"Conversation Title: {conversation_title}\n"
            f"Email Type: {email_type}\n"
            f"Desired Tone: {tone}\n"
            f"Recipient: {recipient_name or 'unknown'}\n"
            f"Sender: {sender_name or 'unknown'}\n"
            f"Executive Summary: {exec_summary}\n"
            f"Next Steps: {', '.join(next_steps)}\n"
            f"Action Items: {', '.join(tasks[:3])}\n"
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_content),
        ]

        if self.llm.provider_name == "mock":
            return self._template_email(conversation_title, exec_summary, next_steps, tasks,
                                        email_type, tone, recipient_name, sender_name)

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
            return self._template_email(conversation_title, exec_summary, next_steps, tasks,
                                        email_type, tone, recipient_name, sender_name)

    @staticmethod
    def _template_email(
        conversation_title: str,
        exec_summary: str,
        next_steps: list[str],
        tasks: list[str],
        email_type: str,
        tone: str,
        recipient_name: Optional[str],
        sender_name: Optional[str],
    ) -> dict[str, Any]:
        """Draft assembled only from stored conversation data (no AI model involved)."""
        follow_ups = next_steps or tasks
        body = [f"Hi {recipient_name or 'there'},", "", f"Thank you for your time on our call ({conversation_title})."]
        if exec_summary:
            body += ["", f"Summary: {exec_summary}"]
        if follow_ups:
            body += ["", "Next steps:", *[f"- {step}" for step in follow_ups[:5]]]
        body += ["", "Best regards,", sender_name or "[Your name]"]
        return {
            "subject": f"Follow-up: {conversation_title}",
            "body": "\n".join(body),
            "suggested_actions": follow_ups[:3],
            "email_type": email_type,
            "tone": tone,
        }
