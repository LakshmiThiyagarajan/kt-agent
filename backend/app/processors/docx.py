from docx import Document
from pathlib import Path

def extract_docx(file_path: Path):
    doc = Document(file_path)
    return "\n".join([p.text for p in doc.paragraphs])