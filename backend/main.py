"""
main.py
-------
KT-Agent FastAPI application entry point.
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.logger import get_logger, setup_logging
from memory.database import init_db
from routes import auth, chat, ingest, profile

# Initialise logging immediately
setup_logging()
logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown lifecycle."""
    logger.info("kt_agent_starting")
    init_db()                                    # Create SQLite tables
    # Pinecone is initialised lazily on first use
    logger.info("kt_agent_ready")
    yield
    logger.info("kt_agent_shutdown")


app = FastAPI(
    title="KT-Agent",
    description="Agentic Knowledge Transfer System",
    version="1.0.0",
    lifespan=lifespan,
)

# ── CORS ──────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routes ────────────────────────────────────────────────────────────────────
app.include_router(auth.router,    prefix="/api/v1")
app.include_router(profile.router, prefix="/api/v1")
app.include_router(chat.router,    prefix="/api/v1")
app.include_router(ingest.router,  prefix="/api/v1")


# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/health", tags=["system"])
async def health():
    return {"status": "ok", "service": "kt-agent"}


# ── Global error handler ──────────────────────────────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    logger.error("unhandled_exception", error=str(exc), path=str(request.url))
    return JSONResponse(status_code=500, content={"detail": "Internal server error."})
