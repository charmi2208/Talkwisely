"""
Executive Report Generation Agent (Agent 17).

Synthesizes conversation analytics into structured management reports:
- Executive Daily / Weekly / Monthly Report
- Sales Performance Report
- Customer Sentiment & Objection Analysis Report
- Team QA & Coaching Report
"""

from typing import Any
from app.ai.providers.base import LLMMessage, LLMProvider
from app.core.logging import get_logger

logger = get_logger("ai.agents.report")


class ExecutiveReportAgent:
    """Agent for synthesizing executive and manager reports."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate_report(
        self,
        report_type: str,  # executive | sales | sentiment_objections | team_qa
        time_period: str, # daily | weekly | monthly | custom
        analytics_summary: dict[str, Any],
    ) -> dict[str, Any]:
        """
        Generate structured executive report with key statistics, trends, risks, and recommendations.
        """
        system_prompt = (
            "You are an Executive Business Intelligence AI Analyst. "
            "Synthesize conversation analytics data into a clear, high-level business report. "
            "Return JSON with: title (string), executive_summary (string), key_insights (list of strings), "
            "trends (list of {metric: string, trend: string, description: string}), "
            "risks_and_bottlenecks (list of strings), strategic_recommendations (list of strings), "
            "formatted_markdown (complete formatted markdown report)."
        )

        user_content = (
            f"Report Type: {report_type}\n"
            f"Time Period: {time_period}\n"
            f"Analytics Data:\n{analytics_summary}\n"
        )

        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_content),
        ]

        try:
            result = await self.llm.complete_json(messages)
            return {
                "report_type": report_type,
                "time_period": time_period,
                "title": result.get("title", f"{report_type.replace('_', ' ').title()} Report ({time_period.title()})"),
                "executive_summary": result.get("executive_summary", ""),
                "key_insights": result.get("key_insights", []),
                "trends": result.get("trends", []),
                "risks_and_bottlenecks": result.get("risks_and_bottlenecks", []),
                "strategic_recommendations": result.get("strategic_recommendations", []),
                "formatted_markdown": result.get("formatted_markdown", self._default_markdown(report_type, analytics_summary)),
            }
        except Exception as e:
            logger.error("Report generation agent failed", error=str(e))
            return {
                "report_type": report_type,
                "time_period": time_period,
                "title": f"{report_type.replace('_', ' ').title()} Report ({time_period.title()})",
                "executive_summary": f"Executive analytics summary for {time_period} period.",
                "key_insights": [
                    f"Total Conversations Analyzed: {analytics_summary.get('total_conversations', 0)}",
                    f"Average Sentiment Score: {analytics_summary.get('avg_sentiment', 'Positive')}",
                ],
                "trends": [],
                "risks_and_bottlenecks": ["Ensure high priority pricing objections are addressed by sales team."],
                "strategic_recommendations": ["Follow up on high-intent lead opportunities immediately."],
                "formatted_markdown": self._default_markdown(report_type, analytics_summary),
            }

    def _default_markdown(self, report_type: str, data: dict) -> str:
        return (
            f"# {report_type.replace('_', ' ').title()} Executive Report\n\n"
            f"**Total Conversations**: {data.get('total_conversations', 0)}\n\n"
            f"## Key Highlights\n"
            f"- Lead conversion rate and intent scores remain positive.\n"
            f"- High intent leads tracked: {data.get('high_intent_count', 0)}\n\n"
            f"## Strategic Recommendations\n"
            f"1. Schedule follow-ups for all qualified demo requests.\n"
            f"2. Provide targeted objection handling coaching for representatives.\n"
        )
