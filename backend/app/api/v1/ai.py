"""
AI Copilot & Intelligence API Router.

POST /api/v1/ai/copilot/chat           — RAG-powered Copilot Chat
POST /api/v1/ai/generate-email         — Generate follow-up email draft
POST /api/v1/ai/natural-language-query — NL-to-Analytics query tool
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.ai.agents.copilot_agent import CopilotAgent
from app.ai.agents.email_agent import EmailGenerationAgent
from app.ai.pipeline.graph import llm_session
from app.core.access import conversation_scope, is_privileged
from app.core.dependencies import get_current_user, get_db
from app.core.logging import get_logger
from app.services.nl_analytics import answer_analytics_question
from app.core.cache import get_or_compute
from app.core.config import settings

router = APIRouter(prefix="/ai", tags=["AI Copilot & Tools"])
logger = get_logger("api.v1.ai")


class CopilotChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    chat_history: Optional[list[dict]] = None


class AnalyticsAnswer(BaseModel):
    tool: str
    title: str
    period: str
    columns: list[str]
    rows: list[list]


class CopilotChatResponse(BaseModel):
    answer: str
    query: str
    citations: list[dict]
    context_count: int
    # Set when the question was answered by a predefined analytics function (exact numbers)
    analytics: Optional[AnalyticsAnswer] = None


class GenerateEmailRequest(BaseModel):
    conversation_id: str
    email_type: str = "thank_you"  # thank_you | meeting_summary | proposal_follow_up | demo_follow_up
    tone: str = "professional"     # professional | friendly | concise | formal
    recipient_name: Optional[str] = None
    sender_name: Optional[str] = None


class GenerateEmailResponse(BaseModel):
    subject: str
    body: str
    suggested_actions: list[str]
    email_type: str
    tone: str


class NLQueryRequest(BaseModel):
    query: str


async def _check_conversation_access(db: AsyncSession, user, conversation_id: Optional[str]) -> None:
    """404 unless ``user`` may see this conversation (no-op when no conversation is given)."""
    if not conversation_id:
        return
    from sqlalchemy import select
    from app.db.models import Conversation

    found = (await db.execute(
        select(Conversation.id).where(Conversation.id == conversation_id, *conversation_scope(user))
    )).first()
    if not found:
        raise HTTPException(status_code=404, detail="Conversation not found")


@router.post("/copilot/chat", response_model=CopilotChatResponse)
async def copilot_chat(
    payload: CopilotChatRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    RAG-powered conversational assistant querying conversations, summaries,
    sales insights, and knowledge base.
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    await _check_conversation_access(db, current_user, payload.conversation_id)

    async with llm_session() as llm:
        # Organization-wide counts, rankings and percentages come from predefined queries
        if not payload.conversation_id:
            analytics = await answer_analytics_question(payload.query.strip(), current_user, db, llm)
            if analytics:
                return CopilotChatResponse(
                    answer=analytics.answer,
                    query=payload.query,
                    citations=[],
                    context_count=0,
                    analytics=AnalyticsAnswer(**analytics.payload()),
                )

        owner_id = None if is_privileged(current_user) else current_user.id

        async def run_copilot() -> dict:
            return await CopilotAgent(llm).answer_question(
                query=payload.query.strip(),
                organization_id=current_user.organization_id,
                conversation_id=payload.conversation_id,
                chat_history=payload.chat_history,
                db_session=db,
                owner_id=owner_id,
            )

        if payload.chat_history:
            result = await run_copilot()  # follow-ups depend on the conversation so far
        else:
            # Same question, same data: reuse the answer. New data changes the cache generation.
            result = await get_or_compute(
                "copilot",
                current_user.organization_id,
                f"user:{owner_id}" if owner_id else "org",
                {"q": " ".join(payload.query.lower().split()), "conversation": payload.conversation_id, "llm": llm.model_name},
                run_copilot,
                ttl=settings.copilot_cache_ttl_seconds,
            )

    return CopilotChatResponse(
        answer=result["answer"],
        query=result["query"],
        citations=result["citations"],
        context_count=result["context_count"],
    )


@router.post("/generate-email", response_model=GenerateEmailResponse)
async def generate_email(
    payload: GenerateEmailRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate a context-aware follow-up email based on conversation insights."""
    from app.db.models import Conversation, Summary, ActionItem, SalesInsight
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload

    # Verify conversation access
    res = await db.execute(
        select(Conversation)
        .options(selectinload(Conversation.summary), selectinload(Conversation.sales_insight))
        .where(
            Conversation.id == payload.conversation_id,
            *conversation_scope(current_user),
        )
    )
    conv = res.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation not found")

    # Fetch action items
    actions_res = await db.execute(
        select(ActionItem).where(ActionItem.conversation_id == payload.conversation_id)
    )
    action_items = actions_res.scalars().all()

    summary_dict = None
    if conv.summary:
        summary_dict = {
            "executive_summary": conv.summary.executive_summary,
            "next_steps": conv.summary.next_steps,
        }

    sales_dict = None
    if conv.sales_insight:
        sales_dict = {
            "lead_score": conv.sales_insight.lead_score,
            "purchase_intent": conv.sales_insight.purchase_intent,
        }

    action_dicts = [{"description": a.description} for a in action_items]

    async with llm_session() as llm:
        agent = EmailGenerationAgent(llm)

        result = await agent.generate_email(
            conversation_title=conv.title,
            summary=summary_dict,
            action_items=action_dicts,
            sales_insight=sales_dict,
            email_type=payload.email_type,
            tone=payload.tone,
            recipient_name=payload.recipient_name,
            sender_name=payload.sender_name or current_user.full_name,
        )

    return GenerateEmailResponse(**result)


@router.post("/natural-language-query")
async def natural_language_query(
    payload: NLQueryRequest,
    current_user=Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Answer an analytics question with a predefined, validated query (never generated SQL).

    Questions that aren't about counts, rankings, averages or percentages fall back to the
    search-based Copilot.
    """
    if not payload.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    async with llm_session() as llm:
        analytics = await answer_analytics_question(payload.query.strip(), current_user, db, llm)
        if analytics:
            return {"query_type": analytics.tool, "answer": analytics.answer, **analytics.payload()}

        res = await CopilotAgent(llm).answer_question(
            query=payload.query,
            organization_id=current_user.organization_id,
            db_session=db,
            owner_id=None if is_privileged(current_user) else current_user.id,
        )
    return {
        "query_type": "rag_search",
        "answer": res["answer"],
        "citations": res["citations"],
    }
