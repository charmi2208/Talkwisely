"""
AI Copilot Agent — RAG & Tool-based Assistant.

Allows users to ask natural language questions across all meetings, calls,
sales insights, tasks, and uploaded knowledge documents.

Context comes from two places:
- semantic search over indexed transcript chunks, summaries and knowledge documents
- structured records read from the database (never LLM-written SQL)
"""

import re
from datetime import date
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.providers.base import LLMMessage, LLMProvider
from app.ai.rag.vector_store import vector_store
from app.core.logging import get_logger
from app.db.models import ActionItem, Conversation, Objection, SalesInsight, SentimentResult, Summary

logger = get_logger("ai.agents.copilot")

NOT_FOUND = "Not found in the available conversations."
MIN_RELEVANCE = 0.2
RETRIEVAL_LIMIT = 6
INDEX_SIZE = 20

def _system_prompt(today: str) -> str:
    return (
        "You are TalkWiseAI Copilot, the assistant inside TalkWiseAI, a conversation-intelligence app that "
        "transcribes and analyzes recorded sales calls, support calls and meetings (summaries, sentiment, intent, "
        "lead scores, objections, action items, CRM proposals) and lets teams search them and their company documents. "
        f"Today is {today}.\n\n"
        "How to answer:\n"
        "- Greetings, thanks, or questions about what you can do or how TalkWiseAI works: reply briefly and helpfully "
        "in one to three sentences, without sources, and suggest an example question.\n"
        "- Questions about calls, customers, deals, tasks or company documents: answer only from the numbered sources "
        "and the records below. Cite sources inline as [1], [2]. Refer to records by conversation title, never with brackets.\n"
        "- Resolve relative dates such as 'this week' or 'yesterday' against today's date and the dates on sources and "
        "records, and leave out conversations outside the requested period.\n"
        "- Give the direct answer first. Only when you add your own deduction or advice, put it on a separate line "
        "starting with 'Inference:' or 'Recommendation:'. Don't label plain facts.\n"
        f"- If the sources and records don't contain the answer, say \"{NOT_FOUND}\" and suggest what to check.\n"
        "- Never invent names, companies, dates, prices, commitments or decisions.\n"
        "- Plain text only; short '-' bullet lists are fine. No markdown headings or bold."
    )


# Some models cite with full-width brackets (【2】); normalize to [2]
_WIDE_CITATION = re.compile(r"【\s*(\d+)\s*(?:†[^】]*)?】")


# "[Records]" isn't a real source
_RECORD_TAG = re.compile(r"\s*\[records?\]", re.IGNORECASE)


def _keep_cited_sources(answer: str, citations: list[dict]) -> tuple[str, list[dict]]:
    """Keep only cited sources and renumber them 1..n in order of first mention."""
    order: list[int] = []
    for n in map(int, re.findall(r"\[(\d+)\]", answer)):
        if n not in order and any(c["source"] == n for c in citations):
            order.append(n)
    renumber = {old: new for new, old in enumerate(order, start=1)}
    answer = re.sub(
        r"\[(\d+)\]",
        lambda m: f"[{renumber[int(m.group(1))]}]" if int(m.group(1)) in renumber else "",
        answer,
    )
    kept = sorted((dict(c, source=renumber[c["source"]]) for c in citations if c["source"] in renumber),
                  key=lambda c: c["source"])
    return answer, kept


def _snippet(text: str, limit: int = 180) -> str:
    text = " ".join(text.split())
    return text if len(text) <= limit else text[:limit].rsplit(" ", 1)[0] + "..."


class CopilotAgent:
    """Multi-tool RAG assistant for TalkWiseAI."""

    def __init__(self, llm: LLMProvider):
        self.llm = llm

    async def answer_question(
        self,
        query: str,
        organization_id: str,
        conversation_id: Optional[str] = None,
        chat_history: Optional[list[dict]] = None,
        db_session: Optional[AsyncSession] = None,
    ) -> dict[str, Any]:
        """Retrieve context, then synthesize a grounded, cited answer."""
        hits = await vector_store.search(
            query=query,
            organization_id=organization_id,
            conversation_id=conversation_id,
            limit=RETRIEVAL_LIMIT,
        )
        hits = [h for h in hits if h.get("score", 0) >= MIN_RELEVANCE]
        # Near-identical chunks add noise without adding evidence
        seen: set[str] = set()
        hits = [h for h in hits if not (h.get("document", "") in seen or seen.add(h.get("document", "")))]

        sources = []
        citations = []
        for n, hit in enumerate(hits, start=1):
            meta = hit.get("metadata", {})
            is_doc = meta.get("doc_type") == "knowledge_base"
            label = meta.get("title", "Untitled")
            if meta.get("date"):
                label += f" | {meta['date']}"
            if meta.get("timestamp"):
                label += f" | at {meta['timestamp']}"
            if meta.get("doc_type") == "summary":
                label += " | summary"
            sources.append(f"[{n}] ({'knowledge base' if is_doc else 'conversation'}: {label})\n{hit.get('document', '')}")
            citations.append({
                "source": n,
                "doc_type": meta.get("doc_type"),
                "conversation_id": meta.get("conversation_id"),
                "document_id": meta.get("document_id"),
                "title": meta.get("title"),
                "timestamp": meta.get("timestamp"),
                "start_time": meta.get("start_time"),
                "speaker": meta.get("speaker"),
                "text_snippet": _snippet(hit.get("document", "")),
                "score": hit.get("score", 0.0),
            })

        records = ""
        if db_session is not None:
            try:
                records = (
                    await self._conversation_records(db_session, organization_id, conversation_id)
                    if conversation_id
                    else await self._organization_index(db_session, organization_id)
                )
            except Exception as e:
                logger.error("Copilot record lookup failed", error=str(e))

        if self.llm.provider_name == "mock":
            answer = self._extractive_answer(citations)
            citations = citations[:4]
        else:
            answer = await self._generate(query, sources, records, chat_history)
            answer, citations = _keep_cited_sources(answer, citations)

        return {
            "answer": answer,
            "query": query,
            "citations": citations,
            "context_count": len(hits),
        }

    async def _generate(
        self, query: str, sources: list[str], records: str, chat_history: Optional[list[dict]]
    ) -> str:
        context = "Sources:\n" + ("\n\n".join(sources) if sources else "(no matching passages)")
        if records:
            context += f"\n\nRecords:\n{records}"

        messages = [LLMMessage(role="system", content=_system_prompt(date.today().strftime("%A, %d %B %Y")))]
        for item in (chat_history or [])[-4:]:  # last two turns for follow-up questions
            role, content = item.get("role"), item.get("content")
            if role in ("user", "assistant") and content:
                messages.append(LLMMessage(role=role, content=content))
        messages.append(LLMMessage(role="user", content=f"{context}\n\nQuestion: {query}"))

        try:
            response = await self.llm.complete(messages, temperature=0.2, max_tokens=700)
            text = _WIDE_CITATION.sub(r"[\1]", response.content)
            return _RECORD_TAG.sub("", text).strip() or NOT_FOUND
        except Exception as e:
            logger.error("LLM completion failed for Copilot agent", error=str(e))
            return "The AI service is unavailable right now, so I couldn't answer. Please try again in a minute."

    @staticmethod
    def _extractive_answer(citations: list[dict]) -> str:
        if not citations:
            return f"{NOT_FOUND} (Mock mode: no AI model is configured, so answers are limited to search results.)"
        lines = [
            "Mock mode: no AI model is configured, so here are the most relevant passages instead of a written answer."
        ]
        for c in citations[:4]:
            where = " at ".join(p for p in (c.get("title"), c.get("timestamp")) if p)
            lines.append(f"- [{c['source']}] {where}: {c['text_snippet']}")
        return "\n".join(lines)

    async def _conversation_records(self, db: AsyncSession, org_id: str, conversation_id: str) -> str:
        conv = (await db.execute(
            select(Conversation).where(Conversation.id == conversation_id, Conversation.organization_id == org_id)
        )).scalar_one_or_none()
        if not conv:
            return ""

        lines = [
            f"Conversation: {conv.title} ({conv.conversation_type}, {conv.created_at.date().isoformat()}, "
            f"{round((conv.duration_seconds or 0) / 60)} min)"
        ]
        summary = (await db.execute(select(Summary).where(Summary.conversation_id == conversation_id))).scalar_one_or_none()
        if summary:
            lines.append(f"Summary: {summary.executive_summary}")
            if summary.decisions:
                lines.append("Decisions: " + "; ".join(map(str, summary.decisions)))
            if summary.next_steps:
                lines.append("Next steps: " + "; ".join(map(str, summary.next_steps)))
        sentiment = (await db.execute(
            select(SentimentResult).where(SentimentResult.conversation_id == conversation_id)
        )).scalar_one_or_none()
        if sentiment:
            lines.append(f"Sentiment: {sentiment.overall_sentiment} (trend: {sentiment.sentiment_trend or 'n/a'})")
        sales = (await db.execute(
            select(SalesInsight).where(SalesInsight.conversation_id == conversation_id)
        )).scalar_one_or_none()
        if sales:
            lines.append(
                f"Sales: lead score {sales.lead_score}, purchase intent {sales.purchase_intent}, "
                f"deal health {sales.deal_health}, budget {sales.budget_range or 'not discussed'}"
            )
        items = (await db.execute(select(ActionItem).where(ActionItem.conversation_id == conversation_id))).scalars().all()
        for item in items:
            lines.append(
                f"Action item: {item.description} (owner: {item.owner or 'unknown'}, "
                f"due: {item.due_date or 'not set'}, status: {item.status})"
            )
        objections = (await db.execute(select(Objection).where(Objection.conversation_id == conversation_id))).scalars().all()
        for obj in objections:
            lines.append(
                f"Objection ({obj.category}, {'resolved' if obj.was_resolved else 'unresolved'}): {obj.description}"
            )
        return "\n".join(lines)

    async def _organization_index(self, db: AsyncSession, org_id: str) -> str:
        rows = (await db.execute(
            select(Conversation, SalesInsight, SentimentResult, Summary)
            .outerjoin(SalesInsight, SalesInsight.conversation_id == Conversation.id)
            .outerjoin(SentimentResult, SentimentResult.conversation_id == Conversation.id)
            .outerjoin(Summary, Summary.conversation_id == Conversation.id)
            .where(Conversation.organization_id == org_id, Conversation.status == "completed")
            .order_by(Conversation.created_at.desc())
            .limit(INDEX_SIZE)
        )).all()
        lines = []
        for conv, sales, sentiment, summary in rows:
            parts = [f"{conv.title} ({conv.conversation_type}, {conv.created_at.date().isoformat()})"]
            if sales and sales.lead_score is not None:
                parts.append(f"lead score {sales.lead_score}, intent {sales.purchase_intent}, deal {sales.deal_health}")
            if sentiment:
                parts.append(f"sentiment {sentiment.overall_sentiment}")
            if summary and summary.executive_summary:
                parts.append(_snippet(summary.executive_summary, 200))
            lines.append("- " + "; ".join(parts))
        return f"Most recent {len(lines)} conversations:\n" + "\n".join(lines) if lines else ""
