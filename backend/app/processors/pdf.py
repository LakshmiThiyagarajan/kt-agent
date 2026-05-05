import pdfplumber
from pathlib import Path

def extract_pdf(file_path: Path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text