"""
Unit tests for AI Providers, Vector Store, and Copilot Agent.
"""

import pytest
import asyncio
from app.ai.providers.llm.mock_provider import MockLLMProvider
from app.ai.providers.embedding.mock_provider import MockEmbeddingProvider
from app.ai.rag.vector_store import VectorStore
from app.ai.agents.copilot_agent import CopilotAgent
from app.ai.agents.email_agent import EmailGenerationAgent


@pytest.mark.asyncio
async def test_mock_llm_provider_completion():
    provider = MockLLMProvider()
    from app.ai.providers.base import LLMMessage
    messages = [LLMMessage(role="user", content="Hello")]
    res = await provider.complete(messages)
    assert res.content is not None
    assert res.model == provider.model_name


@pytest.mark.asyncio
async def test_mock_embedding_provider_dimension():
    embedder = MockEmbeddingProvider()
    vector = await embedder.embed_text("TalkWiseAI Cloud PBX call recording")
    assert len(vector) == 384
    assert isinstance(vector[0], float)


@pytest.mark.asyncio
async def test_vector_store_add_and_search():
    vs = VectorStore()
    doc_ids = ["doc_test_1", "doc_test_2"]
    documents = [
        "TalkWisely Cloud PBX provides UK and USA business numbers.",
        "Sales intelligence platform analyzes customer objections and buying signals.",
    ]
    metadatas = [
        {"organization_id": "org_test", "topic": "pbx"},
        {"organization_id": "org_test", "topic": "sales"},
    ]

    await vs.add_documents(ids=doc_ids, documents=documents, metadatas=metadatas)

    results = await vs.search(
        query="business phone numbers",
        organization_id="org_test",
        limit=2,
    )
    assert len(results) > 0
    assert results[0]["id"] in doc_ids


@pytest.mark.asyncio
async def test_copilot_agent_answering():
    llm = MockLLMProvider()
    agent = CopilotAgent(llm)

    res = await agent.answer_question(
        query="What is the price of Enterprise plan?",
        organization_id="org_test",
    )
    assert "answer" in res
    assert "citations" in res


@pytest.mark.asyncio
async def test_email_generation_agent():
    llm = MockLLMProvider()
    agent = EmailGenerationAgent(llm)

    res = await agent.generate_email(
        conversation_title="Discovery Call",
        summary={"executive_summary": "Discussed PBX migration."},
        email_type="thank_you",
        tone="professional",
    )
    assert "subject" in res
    assert "body" in res
