"""
routes/ingest.py
----------------
Document ingestion endpoint.
Accepts file upload and runs through the Ingestion Agent pipeline.
"""
from __future__ import annotations

from fastapi import APIRouter, File, Form, HTTPException, UploadFile

from agents.ingestion_agent import IngestionAgent
from core.logger import get_logger
from core.schemas import IngestionResult

router = APIRouter(prefix="/ingest", tags=["ingestion"])
logger = get_logger(__name__)

_ingestion_agent = IngestionAgent()

ALLOWED_TYPES = {
    # Documents
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "text/plain",
    "text/markdown",
    # Images (OCR via GPT-4o Vision)
    "image/png",
    "image/jpeg",
    "image/webp",
    "image/gif",
    # Audio (transcription via Whisper)
    "audio/mpeg",
    "audio/mp4",
    "audio/x-m4a",
    "audio/wav",
    "audio/webm",
    "audio/ogg",
    "video/mp4",   # some browsers send mp4 audio as video/mp4
}

MAX_FILE_SIZE = 50 * 1024 * 1024   # 50 MB (audio files can be larger)


@router.post("", response_model=IngestionResult)
async def ingest_document(
    file: UploadFile = File(...),
    uploaded_by: str = Form(default="anonymous"),
    project: str = Form(default=""),
    allow_pii: bool = Form(default=False),
):
    """
    Upload and ingest a document.

    - Runs PII detection → duplicate check → parse → chunk → embed → store.
    - Returns ingestion result including number of chunks stored.
    """
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(
            415,
            f"Unsupported file type: {file.content_type}. "
            f"Allowed: PDF, DOCX, TXT, MD.",
        )

    file_bytes = await file.read()

    if len(file_bytes) > MAX_FILE_SIZE:
        raise HTTPException(413, "File exceeds maximum size of 20 MB.")

    if not file_bytes:
        raise HTTPException(400, "Empty file uploaded.")

    logger.info("ingest_request", filename=file.filename, size=len(file_bytes), by=uploaded_by)

    result = await _ingestion_agent.ingest(
        filename=file.filename or "unknown",
        file_bytes=file_bytes,
        uploaded_by=uploaded_by,
        project=project or None,
        allow_pii=allow_pii,
    )

    if result.status == "error":
        raise HTTPException(422, result.message)

    return result


@router.get("/log")
async def get_ingestion_log(limit: int = 50):
    """Return the ingestion audit log."""
    from memory.database import get_db

    with get_db() as db:
        rows = db.execute(
            "SELECT * FROM ingestion_log ORDER BY id DESC LIMIT ?",
            (limit,),
        ).fetchall()

    return [dict(r) for r in rows]
