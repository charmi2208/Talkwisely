"""
Vector Store Service.

Provides semantic indexing and metadata-filtered retrieval over:
1. Transcript segments
2. Meeting summaries & decisions
3. Uploaded Knowledge Base documents

Supports ChromaDB with an in-memory cosine fallback for fast local execution.
"""

import math
import re
from typing import Any, Optional

from app.ai.providers.embedding import get_embedding_provider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ai.rag.vector_store")


def _where(**conditions: Any) -> dict[str, Any]:
    """Chroma needs an explicit $and when filtering on more than one field."""
    clauses = [{k: v} for k, v in conditions.items() if v is not None]
    if len(clauses) == 1:
        return clauses[0]
    return {"$and": clauses}


def _clean_metadata(meta: dict[str, Any]) -> dict[str, Any]:
    """Chroma metadata values must be primitives and not None."""
    cleaned = {}
    for k, v in meta.items():
        if v is None:
            continue
        cleaned[k] = v if isinstance(v, (str, int, float, bool)) else str(v)
    return cleaned


class VectorStore:
    """Vector database manager supporting organization-scoped filtered RAG queries."""

    def __init__(self):
        self.embedding_provider = get_embedding_provider()
        self._fallback_store: list[dict[str, Any]] = []  # List of {id, vector, document, metadata}
        self._chroma_client = None
        self._collection = None
        self._init_chroma()

    @property
    def is_persistent(self) -> bool:
        return self._collection is not None

    def _init_chroma(self) -> None:
        """Attempt to initialize persistent ChromaDB client."""
        try:
            import chromadb
            self._chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
            # One collection per embedding model: vectors from different models aren't comparable
            suffix = re.sub(r"[^a-zA-Z0-9_-]", "-", self.embedding_provider.provider_name)
            self._collection = self._chroma_client.get_or_create_collection(
                name=f"talkwise_rag_{suffix}",
                metadata={"hnsw:space": "cosine"},
            )
            logger.info(
                "ChromaDB vector store initialized",
                path=settings.chroma_persist_dir,
                collection=self._collection.name,
            )
        except Exception as e:
            logger.warning("ChromaDB initialization fallback to in-memory store", error=str(e))
            self._chroma_client = None
            self._collection = None

    async def add_documents(
        self,
        ids: list[str],
        documents: list[str],
        metadatas: list[dict[str, Any]],
    ) -> None:
        """Add or update documents with metadata into the vector store."""
        if not ids or not documents:
            return

        embeddings = await self.embedding_provider.embed_batch(documents)

        if self._collection:
            try:
                self._collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=[_clean_metadata(m) for m in metadatas],
                )
                return
            except Exception as e:
                logger.error("ChromaDB upsert error, storing in fallback", error=str(e))

        # Fallback in-memory storage
        new_ids = set(ids)
        self._fallback_store = [item for item in self._fallback_store if item["id"] not in new_ids]
        for doc_id, doc, vec, meta in zip(ids, documents, embeddings, metadatas):
            self._fallback_store.append({
                "id": doc_id,
                "document": doc,
                "vector": vec,
                "metadata": meta,
            })

    async def search(
        self,
        query: str,
        organization_id: str,
        limit: int = 5,
        conversation_id: Optional[str] = None,
        doc_type: Optional[str] = None,
    ) -> list[dict[str, Any]]:
        """
        Perform semantic similarity search filtered by organization_id and optional parameters.
        Returns list of {id, document, metadata, score} where score is cosine similarity (0-1).
        """
        query_vec = await self.embedding_provider.embed_text(query)

        if self._collection:
            try:
                results = self._collection.query(
                    query_embeddings=[query_vec],
                    n_results=limit,
                    where=_where(
                        organization_id=organization_id,
                        conversation_id=conversation_id,
                        doc_type=doc_type,
                    ),
                )
                formatted = []
                if results and results.get("ids") and len(results["ids"]) > 0:
                    ids = results["ids"][0]
                    docs = results["documents"][0] if results.get("documents") else []
                    metas = results["metadatas"][0] if results.get("metadatas") else []
                    distances = results["distances"][0] if results.get("distances") else []

                    for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
                        formatted.append({
                            "id": doc_id,
                            "document": doc,
                            "metadata": meta,
                            # Cosine distance -> similarity
                            "score": round(max(0.0, 1.0 - dist), 4),
                        })
                return formatted
            except Exception as e:
                logger.error("ChromaDB query failed, executing fallback search", error=str(e))

        # In-memory cosine similarity search
        results = []
        for item in self._fallback_store:
            meta = item["metadata"]
            if meta.get("organization_id") != organization_id:
                continue
            if conversation_id and meta.get("conversation_id") != conversation_id:
                continue
            if doc_type and meta.get("doc_type") != doc_type:
                continue

            score = self._cosine_similarity(query_vec, item["vector"])
            results.append({
                "id": item["id"],
                "document": item["document"],
                "metadata": item["metadata"],
                "score": round(score, 4),
            })

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:limit]

    async def count(self, **conditions: Any) -> int:
        """Number of stored chunks matching the given metadata."""
        if self._collection:
            try:
                return len(self._collection.get(where=_where(**conditions), include=[])["ids"])
            except Exception as e:
                logger.error("ChromaDB count failed", error=str(e))
        return sum(
            1 for item in self._fallback_store
            if all(item["metadata"].get(k) == v for k, v in conditions.items() if v is not None)
        )

    async def delete_by_conversation(self, conversation_id: str) -> None:
        """Delete all vectors for a deleted conversation."""
        if self._collection:
            try:
                self._collection.delete(where={"conversation_id": conversation_id})
            except Exception as e:
                logger.error("Failed to delete vectors from Chroma", error=str(e))

        self._fallback_store = [
            item for item in self._fallback_store
            if item["metadata"].get("conversation_id") != conversation_id
        ]

    async def delete_by_document(self, document_id: str) -> None:
        """Delete all vectors for a deleted knowledge document."""
        if self._collection:
            try:
                self._collection.delete(where={"document_id": document_id})
            except Exception as e:
                logger.error("Failed to delete document vectors from Chroma", error=str(e))

        self._fallback_store = [
            item for item in self._fallback_store
            if item["metadata"].get("document_id") != document_id
        ]

    def _cosine_similarity(self, vec1: list[float], vec2: list[float]) -> float:
        dot = sum(a * b for a, b in zip(vec1, vec2))
        norm1 = math.sqrt(sum(a * a for a in vec1)) or 1.0
        norm2 = math.sqrt(sum(b * b for b in vec2)) or 1.0
        return max(0.0, dot / (norm1 * norm2))


# Global singleton instance
vector_store = VectorStore()
