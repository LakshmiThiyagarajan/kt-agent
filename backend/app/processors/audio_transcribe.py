from openai import OpenAI
from pathlib import Path
import os

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def extract_audio(file_path: Path):
    audio_file = open(file_path, "rb")

    transcript = client.audio.transcriptions.create(
        model="whisper-1",
        file=audio_file
    )

    return transcript.text
