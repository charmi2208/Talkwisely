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
from app.core.dependencies import get_current_user, get_db
from app.core.logging import get_logger

router = APIRouter(prefix="/ai", tags=["AI Copilot & Tools"])
logger = get_logger("api.v1.ai")


class CopilotChatRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    chat_history: Optional[list[dict]] = None


class CopilotChatResponse(BaseModel):
    answer: str
    query: str
    citations: list[dict]
    context_count: int


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

    async with llm_session() as llm:
        agent = CopilotAgent(llm)

        result = await agent.answer_question(
            query=payload.query.strip(),
            organization_id=current_user.organization_id,
            conversation_id=payload.conversation_id,
            chat_history=payload.chat_history,
            db_session=db,
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
            Conversation.organization_id == current_user.organization_id,
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
    """Translate natural language questions into safe analytics operations."""
    query_lower = payload.query.lower()

    if "high intent" in query_lower or "high-intent" in query_lower:
        from app.db.models import Conversation, SalesInsight
        from sqlalchemy import select
        res = await db.execute(
            select(Conversation)
            .join(SalesInsight)
            .where(
                Conversation.organization_id == current_user.organization_id,
                SalesInsight.purchase_intent == "high",
            )
            .limit(10)
        )
        convs = res.scalars().all()
        return {
            "query_type": "high_intent_leads",
            "count": len(convs),
            "results": [{"id": c.id, "title": c.title, "created_at": c.created_at} for c in convs],
        }

    if "objection" in query_lower:
        from app.db.models import Objection, Conversation
        from sqlalchemy import select, func
        res = await db.execute(
            select(Objection.category, func.count(Objection.id).label("count"))
            .join(Conversation)
            .where(Conversation.organization_id == current_user.organization_id)
            .group_by(Objection.category)
            .order_by(func.count(Objection.id).desc())
        )
        counts = res.all()
        return {
            "query_type": "objection_breakdown",
            "results": [{"category": cat, "count": cnt} for cat, cnt in counts],
        }

    # Fallback to copilot search
    async with llm_session() as llm:
        agent = CopilotAgent(llm)
        res = await agent.answer_question(
            query=payload.query,
            organization_id=current_user.organization_id,
            db_session=db,
        )
    return {
        "query_type": "rag_search",
        "answer": res["answer"],
        "citations": res["citations"],
    }
