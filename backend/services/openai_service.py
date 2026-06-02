"""
services/openai_service.py
---------------------------
Thin wrapper around the OpenAI Python SDK.
Provides chat completion and embedding helpers used by agents and tools.
"""
from __future__ import annotations

from tenacity import retry, stop_after_attempt, wait_exponential

import openai

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)

_client: openai.AsyncOpenAI | None = None


def get_openai_client() -> openai.AsyncOpenAI:
    global _client
    if _client is None:
        _client = openai.AsyncOpenAI(api_key=settings.openai_api_key)
    return _client


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def chat_completion(
    messages: list[dict],
    model: str | None = None,
    temperature: float = 0.2,
    max_tokens: int = 2048,
    json_mode: bool = False,
) -> str:
    """Send a chat completion request and return the text response."""
    client = get_openai_client()
    kwargs: dict = dict(
        model=model or settings.openai_llm_model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )
    if json_mode:
        kwargs["response_format"] = {"type": "json_object"}

    logger.debug("chat_completion_request", model=kwargs["model"], msgs=len(messages))
    resp = await client.chat.completions.create(**kwargs)
    content = resp.choices[0].message.content or ""
    logger.debug("chat_completion_done", tokens=resp.usage.total_tokens if resp.usage else None)
    return content


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def embed_text(text: str) -> list[float]:
    """Return the embedding vector for a single string."""
    client = get_openai_client()
    resp = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=text,
    )
    return resp.data[0].embedding


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def vision_completion(image_bytes: bytes, mime_type: str, prompt: str) -> str:
    """Extract text or describe an image using GPT-4o Vision."""
    import base64
    client = get_openai_client()
    b64 = base64.b64encode(image_bytes).decode()
    resp = await client.chat.completions.create(
        model="gpt-4o",
        messages=[{
            "role": "user",
            "content": [
                {"type": "text", "text": prompt},
                {"type": "image_url", "image_url": {"url": f"data:{mime_type};base64,{b64}", "detail": "high"}},
            ],
        }],
        max_tokens=2048,
    )
    return resp.choices[0].message.content or ""


async def transcribe_audio(filename: str, file_bytes: bytes) -> str:
    """Transcribe audio to text using OpenAI Whisper."""
    import tempfile, os
    from pathlib import Path
    client = get_openai_client()

    ext = Path(filename).suffix.lower()
    logger.info("whisper_transcribe", filename=filename, size=len(file_bytes), ext=ext)

    # Write to a real temp file — Whisper needs a genuine file handle, not BytesIO
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
            tmp.write(file_bytes)
            tmp_path = tmp.name

        with open(tmp_path, "rb") as f:
            response = await client.audio.transcriptions.create(
                model="whisper-1",
                file=f,
            )
        logger.info("whisper_done", filename=filename)
        return response.text
    except Exception as exc:
        logger.error("whisper_error", error=str(exc), filename=filename)
        raise
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=8))
async def embed_batch(texts: list[str]) -> list[list[float]]:
    """Return embeddings for a batch of strings."""
    if not texts:
        return []
    client = get_openai_client()
    resp = await client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
    )
    # Results are returned in the same order as input
    return [d.embedding for d in sorted(resp.data, key=lambda x: x.index)]
