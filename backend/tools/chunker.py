"""
tools/chunker.py
----------------
Splits document text into overlapping chunks for embedding.
Uses a simple recursive character splitter logic without LangChain dependency.
"""
from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass, field

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


@dataclass
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    metadata: dict = field(default_factory=dict)


def chunk_text(
    text: str,
    document_id: str,
    filename: str,
    extra_metadata: dict | None = None,
    chunk_size: int | None = None,
    chunk_overlap: int | None = None,
) -> list[Chunk]:
    """
    Split `text` into overlapping chunks.
    Each chunk gets a deterministic ID based on document_id + position.
    """
    size = chunk_size or settings.chunk_size
    overlap = chunk_overlap or settings.chunk_overlap
    extra_metadata = extra_metadata or {}

    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[Chunk] = []
    current = ""
    idx = 0

    for para in paragraphs:
        # If adding this paragraph exceeds chunk size, flush
        if current and len(current) + len(para) + 2 > size:
            chunk_id = _make_chunk_id(document_id, idx)
            chunk_text_content = current.strip()
            chunks.append(
                Chunk(
                    chunk_id=chunk_id,
                    document_id=document_id,
                    text=chunk_text_content,
                    metadata={
                        "document_id": document_id,
                        "filename": filename,
                        "chunk_index": idx,
                        "text": chunk_text_content,
                        **extra_metadata,
                    },
                )
            )
            idx += 1
            # Keep overlap: last N chars of current chunk
            current = current[-overlap:] + "\n\n" + para if overlap else para
        else:
            current = (current + "\n\n" + para).strip() if current else para

    # Flush remainder
    if current.strip():
        remainder = current.strip()
        chunks.append(
            Chunk(
                chunk_id=_make_chunk_id(document_id, idx),
                document_id=document_id,
                text=remainder,
                metadata={
                    "document_id": document_id,
                    "filename": filename,
                    "chunk_index": idx,
                    "text": remainder,
                    **extra_metadata,
                },
            )
        )

    logger.info("chunked", document_id=document_id, chunks=len(chunks), size=size)
    return chunks


def _make_chunk_id(document_id: str, index: int) -> str:
    """Deterministic chunk ID: hash of document_id + index."""
    raw = f"{document_id}::{index}"
    return hashlib.sha256(raw.encode()).hexdigest()[:32]


def make_document_id(filename: str) -> str:
    """Generate a document-level ID from filename + uuid."""
    base = Path(filename).stem  # noqa: F821
    return f"{base}_{uuid.uuid4().hex[:8]}"


from pathlib import Path  # noqa: E402  (placed after function using it)
