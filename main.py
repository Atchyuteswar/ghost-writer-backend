"""Ghost-Writer API — FastAPI Backend.

Main application entry point. Registers all routers, CORS, and lifespan events.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import nltk
import logging

from config import settings
from services.db import db

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Download NLTK data on startup."""
    logger.info("Downloading NLTK data...")
    nltk.download("stopwords", quiet=True)
    nltk.download("punkt", quiet=True)
    nltk.download("punkt_tab", quiet=True)
    nltk.download("averaged_perceptron_tagger", quiet=True)
    logger.info("NLTK data ready.")

    if db:
        logger.info("Supabase connection verified on startup.")
    else:
        logger.warning("Supabase connection failed on startup. Check credentials.")
    yield


app = FastAPI(
    title="Ghost-Writer API",
    description="Personal AI digital twin backend — learns your texting style and speaks like you",
    version="2.0.0",
    lifespan=lifespan,
)

# ─── CORS ──────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Register Routers ─────────────────────────────────────────
from routers import (
    upload,
    analyze,
    pii,
    generate,
    style_transfer,
    memories,
    battles,
    voice_studio,
    achievements,
    insights,
)

app.include_router(upload.router,         prefix="/upload",         tags=["Upload"])
app.include_router(analyze.router,        prefix="/analyze",        tags=["Analyze"])
app.include_router(pii.router,            prefix="/pii",            tags=["PII"])
app.include_router(generate.router,       prefix="/generate",       tags=["Generate"])
app.include_router(style_transfer.router, prefix="/style-transfer", tags=["Style Transfer"])
app.include_router(memories.router,       prefix="/memories",       tags=["Memories"])
app.include_router(battles.router,        prefix="/battles",        tags=["Battles"])
app.include_router(voice_studio.router)
app.include_router(achievements.router)
app.include_router(insights.router)


# ─── Health Checks ─────────────────────────────────────────────

@app.get("/", tags=["Health"])
async def root():
    return {
        "status": "alive",
        "version": "2.0.0",
        "local_only": settings.LOCAL_ONLY_MODE,
        "endpoints": [
            "/upload",
            "/analyze",
            "/pii",
            "/generate",
            "/style-transfer",
            "/memories",
            "/battles",
            "/voice",
            "/achievements",
            "/insights",
        ],
    }


@app.get("/health", tags=["Health"])
async def health():
    checks = {}

    # Anthropic
    try:
        import anthropic
        if settings.ANTHROPIC_API_KEY:
            anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            checks["anthropic"] = "ok"
        else:
            checks["anthropic"] = "error: ANTHROPIC_API_KEY not set"
    except Exception as e:
        checks["anthropic"] = f"error: {str(e)}"

    # Supabase
    checks["supabase"] = "ok" if db is not None else "error: connection failed"

    # Vector store
    try:
        from services.vector_store import VectorStore
        vs = VectorStore()
        checks["vector_store"] = f"ok ({vs.get_count()} memories stored)"
    except Exception as e:
        checks["vector_store"] = f"error: {str(e)}"

    # Voice service
    try:
        from services.voice_service import VoiceService
        vs_voice = VoiceService()
        provider = "elevenlabs" if vs_voice.use_elevenlabs else "gtts (free fallback)"
        checks["voice"] = f"ok — provider: {provider}"
    except Exception as e:
        checks["voice"] = f"error: {str(e)}"

    all_ok = all("error" not in str(v) for v in checks.values())

    return {
        "status": "healthy" if all_ok else "degraded",
        "version": "2.0.0",
        "local_only_mode": settings.LOCAL_ONLY_MODE,
        "checks": checks,
    }