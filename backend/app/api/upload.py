from fastapi import APIRouter, UploadFile, File, HTTPException
from pathlib import Path
import shutil
import traceback

from app.services.ingestion_pipeline import ingest_file

router = APIRouter()

UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)


@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        file_path = UPLOAD_DIR / file.filename

        with file_path.open("wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # 🔥 This is the magic line now
        ingest_file(file_path, uploaded_by="TL_USER")

        return {
            "message": "File processed successfully",
            "filename": file.filename
        }

    except Exception as e:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))