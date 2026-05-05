from PIL import Image
import pytesseract
from pathlib import Path

def extract_image(file_path: Path):
    img = Image.open(file_path)
    text = pytesseract.image_to_string(img)
    return text

