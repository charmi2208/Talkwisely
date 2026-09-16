"""
Standalone Test Runner for TalkWiseAI.
"""

import asyncio
import sys
import os
import tempfile

# Add backend directory to sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, backend_dir)

# Keep test vectors out of the real search index
os.environ["CHROMA_PERSIST_DIR"] = tempfile.mkdtemp(prefix="talkwise_test_vectors_")

from app.ai.providers.llm.mock_provider import MockLLMProvider
from app.ai.providers.embedding.mock_provider import MockEmbeddingProvider
from app.ai.rag.vector_store import VectorStore
from app.ai.agents.copilot_agent import CopilotAgent
from app.ai.agents.email_agent import EmailGenerationAgent
from app.ai.agents.report_agent import ExecutiveReportAgent


async def run_all_tests():
    print("[TEST] Running TalkWiseAI Unit & Integration Verification Suite...\n")

    # 1. Mock LLM Test
    print("1. Testing LLM Provider...")
    llm = MockLLMProvider()
    from app.ai.providers.base import LLMMessage
    res = await llm.complete([LLMMessage(role="user", content="Hello")])
    assert res.content is not None
    print("   [OK] Mock LLM Provider PASSED")

    # 2. Mock Embedding Test
    print("2. Testing Embedding Provider...")
    embedder = MockEmbeddingProvider()
    vec = await embedder.embed_text("TalkWiseAI Cloud PBX call recording")
    assert len(vec) == 384
    print("   [OK] Embedding Provider PASSED (384-dim)")

    # 3. Vector Store Search Test
    print("3. Testing Vector Store & RAG indexing...")
    vs = VectorStore()
    await vs.add_documents(
        ids=["doc_1"],
        documents=["TalkWisely Cloud PBX provides UK and USA business numbers."],
        metadatas=[{"organization_id": "org_test"}]
    )
    search_res = await vs.search("phone numbers", "org_test", limit=1)
    assert len(search_res) > 0
    print("   [OK] Vector Store RAG Retrieval PASSED")

    # 4. Copilot Agent Test
    print("4. Testing AI Copilot Agent...")
    copilot = CopilotAgent(llm)
    c_res = await copilot.answer_question("Which leads showed interest?", "org_test")
    assert "answer" in c_res
    print("   [OK] AI Copilot Agent PASSED")

    # 5. Email Generation Agent Test
    print("5. Testing Email Generation Agent...")
    email_agent = EmailGenerationAgent(llm)
    e_res = await email_agent.generate_email("Sales Demo", summary={"executive_summary": "Good meeting."})
    assert "subject" in e_res
    print("   [OK] Follow-up Email Agent PASSED")

    # 6. Executive Report Agent Test
    print("6. Testing Executive Report Agent...")
    report_agent = ExecutiveReportAgent(llm)
    r_res = await report_agent.generate_report("executive", "weekly", {"total_conversations": 10})
    assert "formatted_markdown" in r_res
    print("   [OK] Executive Report Agent PASSED\n")

    print("[SUCCESS] ALL TESTS PASSED SUCCESSFULLY! 100% VERIFIED.")


if __name__ == "__main__":
    asyncio.run(run_all_tests())
