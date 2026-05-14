from pathlib import Path
import hashlib

from app.processors.pdf import extract_pdf
from app.processors.docx import extract_docx
from app.processors.image_ocr import extract_image
from app.processors.audio_transcribe import extract_audio
from app.processors.pptx import extract_pptx

from app.utils.chunking import chunk_text
from app.core.embeddings import get_embedding
from app.core.pinecone_client import get_index
from app.core.config import NAMESPACE

from app.core.upload_log import init_db, upload_exists, log_upload

# Ensure DB table exists
init_db()


def compute_hash(file_path: Path) -> str:
    sha256 = hashlib.sha256()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            sha256.update(chunk)
    return sha256.hexdigest()


def extract_text(file_path: Path):
    ext = file_path.suffix.lower()

    if ext == ".pdf":
        return extract_pdf(file_path)

    elif ext == ".docx":
        return extract_docx(file_path)

    elif ext == ".pptx":
        return extract_pptx(file_path)

    elif ext in [".png", ".jpg", ".jpeg"]:
        return extract_image(file_path)

    elif ext in [".mp3", ".wav", ".m4a"]:
        return extract_audio(file_path)

    else:
        raise Exception("Unsupported file type")


def ingest_file(file_path: Path, uploaded_by: str):
    file_hash = compute_hash(file_path)

    # 🚫 Stop duplicate uploads
    if upload_exists(file_hash):
        print("⚠️ File already uploaded. Skipping ingestion.")
        return

    text = extract_text(file_path)

    if not text.strip():
        raise Exception("No text extracted from file")

    chunks = chunk_text(text)
    index = get_index()

    for i, chunk in enumerate(chunks):
        vector = get_embedding(chunk)

        metadata = {
            "text": chunk,
            "source": file_path.name,
            "uploaded_by": uploaded_by,
            "type": file_path.suffix
        }

        index.upsert(
            vectors=[
                (f"{file_path.name}_{i}", vector, metadata)
            ],
            namespace=NAMESPACE
        )

    log_upload(
        file_hash=file_hash,
        file_name=file_path.name,
        chunks=len(chunks),
        uploaded_by=uploaded_by
    )

    print("Upload completed and logged.")