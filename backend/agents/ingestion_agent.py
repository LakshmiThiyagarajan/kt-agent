"""
agents/ingestion_agent.py
--------------------------
AGENT 1: INGESTION AGENT

Pipeline:
  Upload → Parse → Duplicate Check → PII Detection
         → Chunking → Embedding → Pinecone Storage → Audit Log

All steps are synchronous except parse and embedding (async).
"""
from __future__ import annotations

from core.logger import get_logger
from core.schemas import IngestionResult
from memory.database import get_db
from services.openai_service import embed_batch
from services.pinecone_service import upsert_vectors
from tools.chunker import Chunk, chunk_text, make_document_id
from tools.document_parser import parse_document
from tools.duplicate_detector import is_duplicate, register_document
from tools.pii_detector import detect_pii

logger = get_logger(__name__)


class IngestionAgent:
    """
    Stateless agent — call `ingest()` for each document.
    """

    async def ingest(
        self,
        filename: str,
        file_bytes: bytes,
        uploaded_by: str | None = None,
        project: str | None = None,
        allow_pii: bool = False,
    ) -> IngestionResult:
        """
        Run the full ingestion pipeline.

        Args:
            filename:    Original filename.
            file_bytes:  Raw file content.
            uploaded_by: employee_id of the uploader (for audit log).
            project:     Project tag for metadata filtering.
            allow_pii:   If True, store PII-redacted text but don't reject.

        Returns:
            IngestionResult with pipeline outcome.
        """
        document_id = make_document_id(filename)
        logger.info("ingestion_started", document_id=document_id, filename=filename)

        # ── Step 1: Parse ─────────────────────────────────────────────────────
        try:
            parsed = await parse_document(filename, file_bytes)
        except ValueError as exc:
            logger.error("parse_failed", error=str(exc))
            return IngestionResult(
                document_id=document_id,
                filename=filename,
                chunks_stored=0,
                pii_detected=False,
                duplicate=False,
                status="error",
                message=str(exc),
            )

        raw_text = parsed.raw_text
        if not raw_text.strip():
            return IngestionResult(
                document_id=document_id,
                filename=filename,
                chunks_stored=0,
                pii_detected=False,
                duplicate=False,
                status="error",
                message="Document appears to be empty.",
            )

        # ── Step 2: Duplicate Check (before PII — fast rejection, no heavy scan) ──
        original_raw_text = raw_text  # keep original for dedup registration later
        dup, existing_id = is_duplicate(original_raw_text)
        if dup:
            return IngestionResult(
                document_id=existing_id,
                filename=filename,
                chunks_stored=0,
                pii_detected=False,
                duplicate=True,
                status="duplicate",
                message=f"Document already exists (id={existing_id}).",
            )

        # ── Step 3: PII Detection ─────────────────────────────────────────────
        pii_result = detect_pii(raw_text)
        if pii_result.has_pii:
            logger.warning("pii_found", document_id=document_id, count=len(pii_result.findings))
            if not allow_pii:
                return IngestionResult(
                    document_id=document_id,
                    filename=filename,
                    chunks_stored=0,
                    pii_detected=True,
                    duplicate=False,
                    status="rejected_pii",
                    message=f"PII detected ({len(pii_result.findings)} instances). Upload rejected.",
                )
            raw_text = pii_result.redacted_text

        # ── Step 4: Chunk ─────────────────────────────────────────────────────
        extra_meta: dict = {"filename": filename}
        if project:
            extra_meta["project"] = project
        if uploaded_by:
            extra_meta["uploaded_by"] = uploaded_by

        chunks: list[Chunk] = chunk_text(
            text=raw_text,
            document_id=document_id,
            filename=filename,
            extra_metadata=extra_meta,
        )

        if not chunks:
            return IngestionResult(
                document_id=document_id,
                filename=filename,
                chunks_stored=0,
                pii_detected=pii_result.has_pii,
                duplicate=False,
                status="error",
                message="Chunking produced 0 chunks.",
            )

        # ── Step 5: Embed ─────────────────────────────────────────────────────
        texts = [c.text for c in chunks]
        logger.info("embedding_chunks", count=len(texts))
        vectors_raw = await embed_batch(texts)

        # ── Step 6: Pinecone Storage ──────────────────────────────────────────
        pinecone_vectors = [
            {
                "id": chunks[i].chunk_id,
                "values": vectors_raw[i],
                "metadata": chunks[i].metadata,
            }
            for i in range(len(chunks))
        ]
        upsert_vectors(pinecone_vectors)

        # ── Step 7: Register hash (dedup future uploads) ──────────────────────
        register_document(original_raw_text, document_id, filename)

        # ── Step 8: Audit Log ─────────────────────────────────────────────────
        self._write_audit_log(
            document_id=document_id,
            filename=filename,
            uploaded_by=uploaded_by,
            chunks_stored=len(chunks),
            pii_detected=pii_result.has_pii,
        )

        logger.info(
            "ingestion_complete",
            document_id=document_id,
            chunks=len(chunks),
        )
        return IngestionResult(
            document_id=document_id,
            filename=filename,
            chunks_stored=len(chunks),
            pii_detected=pii_result.has_pii,
            duplicate=False,
            status="success",
            message=f"Ingested {len(chunks)} chunks successfully.",
        )

    @staticmethod
    def _write_audit_log(
        document_id: str,
        filename: str,
        uploaded_by: str | None,
        chunks_stored: int,
        pii_detected: bool,
    ) -> None:
        try:
            with get_db() as db:
                db.execute(
                    """
                    INSERT INTO ingestion_log
                        (document_id, filename, uploaded_by, chunks_stored, pii_detected, status)
                    VALUES (?, ?, ?, ?, ?, 'success')
                    """,
                    (document_id, filename, uploaded_by, chunks_stored, int(pii_detected)),
                )
        except Exception as exc:
            logger.error("audit_log_failed", error=str(exc))
