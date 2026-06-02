"""
services/pinecone_service.py
-----------------------------
Manages the Pinecone index connection and upsert / query operations.
"""
from __future__ import annotations

from typing import Optional

from pinecone import Pinecone, ServerlessSpec

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_pinecone: Pinecone | None = None
_index = None                          # pinecone.Index

EMBEDDING_DIM = 1536                   # text-embedding-3-small


def get_pinecone_index():
    global _pinecone, _index
    if _index is not None:
        return _index

    _pinecone = Pinecone(api_key=settings.pinecone_api_key)

    existing = [idx.name for idx in _pinecone.list_indexes()]
    if settings.pinecone_index_name not in existing:
        logger.info("creating_pinecone_index", name=settings.pinecone_index_name)
        _pinecone.create_index(
            name=settings.pinecone_index_name,
            dimension=EMBEDDING_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region=settings.pinecone_environment),
        )

    _index = _pinecone.Index(settings.pinecone_index_name)
    logger.info("pinecone_index_ready", name=settings.pinecone_index_name)
    return _index


def upsert_vectors(
    vectors: list[dict],          # [{"id": str, "values": list[float], "metadata": dict}]
    namespace: str = "default",
) -> int:
    """Upsert vectors in batches of 100. Returns total upserted count."""
    index = get_pinecone_index()
    total = 0
    batch_size = 100
    for i in range(0, len(vectors), batch_size):
        batch = vectors[i : i + batch_size]
        index.upsert(vectors=batch, namespace=namespace)
        total += len(batch)
    logger.info("vectors_upserted", count=total, namespace=namespace)
    return total


def query_vectors(
    query_vector: list[float],
    top_k: int = 5,
    namespace: str = "default",
    filter: Optional[dict] = None,
) -> list[dict]:
    """Query similar vectors and return matches with metadata."""
    index = get_pinecone_index()
    kwargs: dict = dict(
        vector=query_vector,
        top_k=top_k,
        include_metadata=True,
        namespace=namespace,
    )
    if filter:
        kwargs["filter"] = filter

    result = index.query(**kwargs)
    matches = []
    for m in result.matches:
        matches.append({
            "id": m.id,
            "score": m.score,
            "metadata": m.metadata or {},
        })
    return matches


def delete_by_document(document_id: str, namespace: str = "default") -> None:
    index = get_pinecone_index()
    index.delete(filter={"document_id": {"$eq": document_id}}, namespace=namespace)
    logger.info("vectors_deleted", document_id=document_id)


def delete_all_vectors(namespace: str = "default") -> None:
    index = get_pinecone_index()
    index.delete(delete_all=True, namespace=namespace)
    logger.info("all_vectors_deleted", namespace=namespace)


def fetch_vector_ids(prefix: str, namespace: str = "default") -> list[str]:
    """List vector IDs by prefix (used for duplicate detection)."""
    index = get_pinecone_index()
    results = index.list(prefix=prefix, namespace=namespace)
    return list(results)
