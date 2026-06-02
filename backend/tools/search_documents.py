"""
tools/search_documents.py
--------------------------
Semantic search against Pinecone.
Returns ranked text chunks and their source metadata.
"""
from __future__ import annotations

from dataclasses import dataclass

from core.logger import get_logger
from services.openai_service import embed_text
from services.pinecone_service import query_vectors

logger = get_logger(__name__)


@dataclass
class SearchResult:
    chunk_id: str
    text: str
    score: float
    filename: str
    document_id: str
    metadata: dict


async def search_documents(
    query: str,
    top_k: int = 5,
    project_filter: str | None = None,
) -> list[SearchResult]:
    """
    Embed the query and retrieve top-k similar chunks from Pinecone.

    Args:
        query:          Natural language query string.
        top_k:          Number of results to retrieve.
        project_filter: Optional project tag to restrict search scope.
    """
    logger.info("search_documents", query=query[:80], top_k=top_k, project=project_filter)

    query_vector = await embed_text(query)

    pinecone_filter = None
    if project_filter:
        pinecone_filter = {"project": {"$eq": project_filter}}

    matches = query_vectors(
        query_vector=query_vector,
        top_k=top_k,
        filter=pinecone_filter,
    )

    results: list[SearchResult] = []
    for m in matches:
        meta = m["metadata"]
        results.append(
            SearchResult(
                chunk_id=m["id"],
                text=meta.get("text", "") or meta.get("chunk_text", ""),
                score=m["score"],
                filename=meta.get("filename", "unknown"),
                document_id=meta.get("document_id", ""),
                metadata=meta,
            )
        )

    logger.info("search_results", count=len(results))
    return results
