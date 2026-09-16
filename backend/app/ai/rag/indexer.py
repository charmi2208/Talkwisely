"""
Conversation indexing for semantic search (RAG).

Turns a processed conversation into searchable chunks:
- transcript windows (a few consecutive segments, with speaker + timestamp)
- one summary chunk (executive summary, topics, decisions, next steps)

Uses a sync SQLAlchemy session because it runs from the background worker
and from scripts, which both use sync sessions.
"""

from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.ai.rag.vector_store import vector_store
from app.core.logging import get_logger
from app.db.models import Conversation, KnowledgeChunk, KnowledgeDocument, Summary, TranscriptSegment

logger = get_logger("ai.rag.indexer")

MAX_CHUNK_CHARS = 700
MAX_SEGMENTS_PER_CHUNK = 6


def format_timestamp(seconds: float) -> str:
    m, s = divmod(int(seconds or 0), 60)
    return f"{m:02d}:{s:02d}"


def _transcript_chunks(segments: list[TranscriptSegment]) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current: list[TranscriptSegment] = []
    size = 0

    def flush() -> None:
        if not current:
            return
        speakers = {seg.speaker_label or "Speaker" for seg in current}
        chunks.append({
            "text": "\n".join(
                f"[{format_timestamp(seg.start_time)}] {seg.speaker_label or 'Speaker'}: {seg.text}" for seg in current
            ),
            "start_time": float(current[0].start_time or 0),
            "speaker": speakers.pop() if len(speakers) == 1 else "Multiple speakers",
            "first_index": current[0].sequence_index,
        })

    for seg in segments:
        line_len = len(seg.text or "") + 20
        if current and (size + line_len > MAX_CHUNK_CHARS or len(current) >= MAX_SEGMENTS_PER_CHUNK):
            flush()
            current, size = [], 0
        current.append(seg)
        size += line_len
    flush()
    return chunks


def _summary_text(summary: Summary) -> str:
    parts = [summary.executive_summary or ""]
    if summary.key_topics:
        parts.append("Key topics: " + ", ".join(map(str, summary.key_topics)))
    if summary.decisions:
        parts.append("Decisions: " + "; ".join(map(str, summary.decisions)))
    if summary.next_steps:
        parts.append("Next steps: " + "; ".join(map(str, summary.next_steps)))
    return "\n".join(p for p in parts if p)


async def index_conversation(db: Session, conversation_id: str) -> int:
    """(Re)index one conversation. Returns the number of chunks stored."""
    conv = db.get(Conversation, conversation_id)
    if not conv:
        return 0

    segments = db.execute(
        select(TranscriptSegment)
        .where(TranscriptSegment.conversation_id == conversation_id)
        .order_by(TranscriptSegment.sequence_index, TranscriptSegment.start_time)
    ).scalars().all()
    summary = db.execute(select(Summary).where(Summary.conversation_id == conversation_id)).scalar_one_or_none()

    base_meta = {
        "organization_id": conv.organization_id,
        "conversation_id": conv.id,
        "title": conv.title,
        "conversation_type": conv.conversation_type,
        "date": (conv.occurred_at or conv.created_at).date().isoformat(),
    }

    ids: list[str] = []
    docs: list[str] = []
    metas: list[dict[str, Any]] = []

    for chunk in _transcript_chunks(list(segments)):
        ids.append(f"{conv.id}_seg_{chunk['first_index']}")
        docs.append(chunk["text"])
        metas.append({
            **base_meta,
            "doc_type": "transcript",
            "speaker": chunk["speaker"],
            "start_time": chunk["start_time"],
            "timestamp": format_timestamp(chunk["start_time"]),
        })

    if summary and (text := _summary_text(summary)):
        ids.append(f"{conv.id}_summary")
        docs.append(text)
        metas.append({**base_meta, "doc_type": "summary"})

    # Replace whatever was indexed before so re-runs don't leave stale chunks
    await vector_store.delete_by_conversation(conv.id)
    await vector_store.add_documents(ids=ids, documents=docs, metadatas=metas)
    logger.info("Conversation indexed", conversation_id=conv.id, chunks=len(ids))
    return len(ids)


async def index_missing_knowledge(db: Session) -> int:
    """Re-embed knowledge documents whose chunks aren't in the vector store (e.g. after a model change)."""
    docs = db.execute(select(KnowledgeDocument)).scalars().all()
    indexed = 0
    for doc in docs:
        if await vector_store.count(organization_id=doc.organization_id, document_id=doc.id) > 0:
            continue
        chunks = db.execute(
            select(KnowledgeChunk).where(KnowledgeChunk.document_id == doc.id).order_by(KnowledgeChunk.chunk_index)
        ).scalars().all()
        if not chunks:
            continue
        await vector_store.add_documents(
            ids=[c.vector_id or f"{doc.id}_chunk_{c.chunk_index}" for c in chunks],
            documents=[c.text for c in chunks],
            metadatas=[{
                "organization_id": doc.organization_id,
                "document_id": doc.id,
                "title": doc.title,
                "category": (c.extra_metadata or {}).get("category", "general"),
                "doc_type": "knowledge_base",
                "chunk_index": c.chunk_index,
            } for c in chunks],
        )
        indexed += 1
    return indexed


async def index_missing_conversations(db: Session) -> int:
    """Index completed conversations that have nothing in the vector store yet."""
    convs = db.execute(select(Conversation).where(Conversation.status == "completed")).scalars().all()
    indexed = 0
    for conv in convs:
        if await vector_store.count(organization_id=conv.organization_id, conversation_id=conv.id) == 0:
            if await index_conversation(db, conv.id):
                indexed += 1
    return indexed
