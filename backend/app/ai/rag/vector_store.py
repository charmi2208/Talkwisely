"""
Vector Store Service.

Provides semantic indexing and metadata-filtered retrieval over:
1. Transcript segments
2. Meeting summaries & decisions
3. Uploaded Knowledge Base documents

Supports ChromaDB with an in-memory cosine fallback for fast local execution.
"""

import math
from typing import Any, Optional
from app.ai.providers.embedding.mock_provider import MockEmbeddingProvider
from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger("ai.rag.vector_store")


class VectorStore:
    """Vector database manager supporting organization-scoped filtered RAG queries."""

    def __init__(self):
        self.embedding_provider = MockEmbeddingProvider()
        self._fallback_store: list[dict[str, Any]] = []  # List of {id, vector, document, metadata}
        self._chroma_client = None
        self._collection = None
        self._init_chroma()

    def _init_chroma(self) -> None:
        """Attempt to initialize persistent ChromaDB client."""
        try:
            import chromadb
            self._chroma_client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
            self._collection = self._chroma_client.get_or_create_collection(
                name="talkwise_rag",
                metadata={"hnsw:space": "cosine"}
            )
            logger.info("ChromaDB vector store initialized successfully", path=settings.chroma_persist_dir)
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
                # Sanitize metadatas for Chroma (ensure primitive types)
                cleaned_metadatas = []
                for meta in metadatas:
                    cleaned = {}
                    for k, v in meta.items():
                        if isinstance(v, (str, int, float, bool)):
                            cleaned[k] = v
                        else:
                            cleaned[k] = str(v)
                    cleaned_metadatas.append(cleaned)

                self._collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=documents,
                    metadatas=cleaned_metadatas,
                )
                return
            except Exception as e:
                logger.error("ChromaDB upsert error, storing in fallback", error=str(e))

        # Fallback in-memory storage
        for doc_id, doc, vec, meta in zip(ids, documents, embeddings, metadatas):
            # Remove existing duplicate ID
            self._fallback_store = [item for item in self._fallback_store if item["id"] != doc_id]
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
        Returns list of {id, document, metadata, score}.
        """
        query_vec = await self.embedding_provider.embed_text(query)

        if self._collection:
            try:
                where_clause: dict[str, Any] = {"organization_id": organization_id}
                if conversation_id:
                    where_clause["conversation_id"] = conversation_id
                if doc_type:
                    where_clause["doc_type"] = doc_type

                results = self._collection.query(
                    query_embeddings=[query_vec],
                    n_results=limit,
                    where=where_clause,
                )
                formatted = []
                if results and results.get("ids") and len(results["ids"]) > 0:
                    ids = results["ids"][0]
                    docs = results["documents"][0] if results.get("documents") else []
                    metas = results["metadatas"][0] if results.get("metadatas") else []
                    distances = results["distances"][0] if results.get("distances") else []

                    for doc_id, doc, meta, dist in zip(ids, docs, metas, distances):
                        # Convert cosine distance to similarity score
                        score = round(max(0.0, 1.0 - (dist / 2.0)), 4)
                        formatted.append({
                            "id": doc_id,
                            "document": doc,
                            "metadata": meta,
                            "score": score,
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
