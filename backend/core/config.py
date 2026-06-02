"""
core/config.py
--------------
Centralised settings loaded from .env via pydantic-settings.
All other modules import `settings` from here — never read os.environ directly.
"""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ── OpenAI ────────────────────────────────────────────────────────────────
    openai_api_key: str
    openai_llm_model: str = "gpt-4o"
    openai_embedding_model: str = "text-embedding-3-small"

    # ── Pinecone ──────────────────────────────────────────────────────────────
    pinecone_api_key: str
    pinecone_index_name: str = "kt-agent"
    pinecone_environment: str = "us-east-1-aws"

    # ── SQLite ────────────────────────────────────────────────────────────────
    sqlite_db_path: str = "./data/kt_agent.db"

    # ── App ───────────────────────────────────────────────────────────────────
    app_secret_key: str = "change-me"
    log_level: str = "INFO"
    cors_origins: str = "http://localhost:3000,http://127.0.0.1:5500"

    # ── Chunking ──────────────────────────────────────────────────────────────
    chunk_size: int = 800
    chunk_overlap: int = 100

    @property
    def cors_origins_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",")]

    @property
    def db_path(self) -> Path:
        p = Path(self.sqlite_db_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        return p


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
