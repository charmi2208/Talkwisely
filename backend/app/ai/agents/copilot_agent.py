"""
AI Copilot Agent — RAG & Tool-based Assistant.

Allows users to ask natural language questions across all meetings, calls,
sales insights, tasks, and uploaded knowledge documents.
"""

from typing import Any, Optional
from app.ai.providers.base import LLMMessage, LLMProvider
from app.ai.rag.vector_store import vector_store
from app.core.logging import get_logger

logger = get_logger("ai.agents.copilot")


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
        db_session: Any = None,
    ) -> dict[str, Any]:
        """
        Execute RAG retrieval, invoke tools as needed, and synthesize a grounded answer.
        """
        # Step 1: Perform vector search for relevant context
        search_results = await vector_store.search(
            query=query,
            organization_id=organization_id,
            conversation_id=conversation_id,
            limit=6,
        )

        context_chunks = []
        citations = []
        for res in search_results:
            meta = res.get("metadata", {})
            title = meta.get("title", meta.get("conversation_id", "Conversation"))
            speaker = meta.get("speaker", "Speaker")
            timestamp = meta.get("timestamp", "00:00")
            doc_text = res.get("document", "")

            context_chunks.append(f"[{title} | {timestamp} | {speaker}]: {doc_text}")
            citations.append({
                "conversation_id": meta.get("conversation_id"),
                "title": title,
                "timestamp": timestamp,
                "speaker": speaker,
                "text_snippet": doc_text[:150] + "..." if len(doc_text) > 150 else doc_text,
                "score": res.get("score", 0.0),
            })

        context_str = "\n".join(context_chunks) if context_chunks else "No specific transcript matches found."

        # Step 2: System prompt with groundedness constraints
        system_prompt = (
            "You are TalkWiseAI Copilot, an expert AI assistant for sales intelligence and meeting analytics. "
            "Answer the user's question based strictly on the provided context retrieved from recorded conversations, "
            "meeting minutes, sales pipeline insights, and company knowledge base.\n\n"
            "Rules:\n"
            "1. Be concise, direct, clear, and actionable.\n"
            "2. Always reference specific timestamps or conversations if available in the context.\n"
            "3. Clearly distinguish between FACT (directly stated in transcript), INFERENCE (logical deduction), "
            "and RECOMMENDATION (suggested next action).\n"
            "4. If the retrieved context does not contain enough information to answer, state clearly: "
            "'Information not found in the available conversation history.' Do not invent commitments, dates, or prices."
        )

        user_content = f"Context:\n{context_str}\n\nUser Question: {query}"

        messages = [LLMMessage(role="system", content=system_prompt)]

        if chat_history:
            for item in chat_history[-4:]:  # Include last 2 turns
                role = item.get("role", "user")
                content = item.get("content", "")
                if role in ("user", "assistant") and content:
                    messages.append(LLMMessage(role=role, content=content))

        messages.append(LLMMessage(role="user", content=user_content))

        try:
            response = await self.llm.complete(messages, temperature=0.2)
            answer_text = response.content
        except Exception as e:
            logger.error("LLM completion failed for Copilot agent", error=str(e))
            answer_text = f"Based on available records: Query processed regarding '{query}'. (AI Provider notice: {str(e)})"

        return {
            "answer": answer_text,
            "query": query,
            "citations": citations,
            "context_count": len(search_results),
        }
