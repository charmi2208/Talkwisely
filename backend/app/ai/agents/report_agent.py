"""
Executive Report Generation Agent (Agent 17).

Synthesizes conversation analytics into structured management reports:
- Executive Daily / Weekly / Monthly Report
- Sales Performance Report
- Customer Sentiment & Objection Analysis Report
- Team QA & Coaching Report
"""

import json
from typing import Any

from app.ai.providers.base import LLMMessage, LLMProvider
from app.core.logging import get_logger

logger = get_logger("ai.agents.report")

REPORT_FOCUS = {
    "executive": "overall conversation volume, sentiment, sales pipeline and open work",
    "sales": "lead scores, purchase intent, deal health and sales objections",
    "sentiment_objections": "customer sentiment and the objections customers raised",
    "team_qa": "agent quality scores and coaching needs",
}


class ExecutiveReportAgent:
    """Agent for synthesizing executive and manager reports."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def generate_report(
        self,
        report_type: str,  # executive | sales | sentiment_objections | team_qa
        time_period: str,  # daily | weekly | monthly
        analytics_summary: dict[str, Any],
    ) -> dict[str, Any]:
        """Generate a structured report grounded in the supplied metrics."""
        title = f"{report_type.replace('_', ' ').title()} Report ({time_period.title()})"
        if self.llm.provider_name == "mock" or not analytics_summary.get("total_conversations"):
            return self._data_report(report_type, time_period, title, analytics_summary)

        system_prompt = (
            "You are a business intelligence analyst writing a management report about recorded sales and "
            "support conversations. Use ONLY the metrics provided. Do not invent numbers, percentages, names or "
            "comparisons with earlier periods (no earlier data is provided). If a metric is zero or missing, say so. "
            f"Focus on {REPORT_FOCUS.get(report_type, REPORT_FOCUS['executive'])}. "
            "Return JSON with: executive_summary (2-4 sentences), key_insights (list of strings, each citing a metric), "
            "risks_and_bottlenecks (list of strings), strategic_recommendations (list of strings, each tied to a metric)."
        )
        user_content = (
            f"Report type: {report_type}\nPeriod: {time_period}\n"
            f"Metrics (JSON):\n{json.dumps(analytics_summary, indent=2, default=str)}"
        )
        messages = [
            LLMMessage(role="system", content=system_prompt),
            LLMMessage(role="user", content=user_content),
        ]

        try:
            result = await self.llm.complete_json(messages)
        except Exception as e:
            logger.error("Report generation agent failed", error=str(e))
            return self._data_report(report_type, time_period, title, analytics_summary)

        report = {
            "report_type": report_type,
            "time_period": time_period,
            "title": title,
            "executive_summary": str(result.get("executive_summary", "")),
            "key_insights": [str(x) for x in result.get("key_insights", [])],
            "trends": [],
            "risks_and_bottlenecks": [str(x) for x in result.get("risks_and_bottlenecks", [])],
            "strategic_recommendations": [str(x) for x in result.get("strategic_recommendations", [])],
        }
        report["formatted_markdown"] = self._markdown(report)
        return report

    def _data_report(self, report_type: str, time_period: str, title: str, data: dict[str, Any]) -> dict[str, Any]:
        """Report built directly from the metrics, used without an AI model or when it fails."""
        total = data.get("total_conversations", 0)
        insights = [f"Conversations analyzed: {total}"]
        if total:
            if data.get("avg_lead_score") is not None:
                insights.append(f"Average lead score: {data['avg_lead_score']}/100")
            insights.append(f"High purchase-intent conversations: {data.get('high_intent_count', 0)}")
            if data.get("sentiment_distribution"):
                insights.append("Sentiment: " + ", ".join(f"{k} {v}" for k, v in data["sentiment_distribution"].items()))
            if data.get("top_objections"):
                insights.append("Most common objections: " + ", ".join(
                    f"{o['category']} ({o['count']})" for o in data["top_objections"]))
            if data.get("avg_agent_score") is not None:
                insights.append(f"Average agent QA score: {data['avg_agent_score']}/100")
            insights.append(f"Open action items: {data.get('open_action_items', 0)}")

        report = {
            "report_type": report_type,
            "time_period": time_period,
            "title": title,
            "executive_summary": (
                f"{total} conversation(s) were analyzed in this {time_period} period."
                if total else f"No conversations were analyzed in this {time_period} period."
            ),
            "key_insights": insights,
            "trends": [],
            "risks_and_bottlenecks": [],
            "strategic_recommendations": [],
        }
        report["formatted_markdown"] = self._markdown(report)
        return report

    @staticmethod
    def _markdown(report: dict[str, Any]) -> str:
        lines = [f"# {report['title']}", "", report["executive_summary"], ""]
        for heading, key in (
            ("Key insights", "key_insights"),
            ("Risks", "risks_and_bottlenecks"),
            ("Recommendations", "strategic_recommendations"),
        ):
            if report.get(key):
                lines += [f"## {heading}", *[f"- {item}" for item in report[key]], ""]
        return "\n".join(lines).strip()
