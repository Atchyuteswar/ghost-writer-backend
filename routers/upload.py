"""Ghost-Writer Backend — Upload Router.

POST /upload — Accept multipart file uploads, validate, parse, and return structured messages.
"""
import logging
from fastapi import APIRouter, UploadFile, File, Form, HTTPException

from config import settings
from services.parser import ChatParser
from models.schemas import UploadResponse

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=UploadResponse)
async def upload_file(
    file: UploadFile = File(...),
    platform: str = Form(default=""),
):
    """Upload a chat export file for parsing."""

    # ─── Validate file extension ──────────────────────────
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if ext not in ("json", "txt", "csv"):
        raise HTTPException(
            status_code=415,
            detail="Unsupported file type. Please upload .json, .txt, or .csv files.",
        )

    # ─── Read file content ────────────────────────────────
    try:
        content = await file.read()
    except Exception as e:
        logger.error(f"Failed to read file: {e}")
        raise HTTPException(status_code=500, detail="Failed to read uploaded file.")

    # ─── Validate file size ───────────────────────────────
    max_bytes = settings.MAX_FILE_SIZE_MB * 1024 * 1024
    if len(content) > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size is {settings.MAX_FILE_SIZE_MB} MB.",
        )

    # ─── Validate not empty ───────────────────────────────
    if len(content) == 0:
        raise HTTPException(status_code=422, detail="File is empty.")

    # ─── Parse ────────────────────────────────────────────
    try:
        messages, warnings = ChatParser.parse_file(filename, content)
    except Exception as e:
        logger.exception(f"Parse failed for {filename}")
        raise HTTPException(status_code=500, detail=f"Parsing failed: {str(e)}")

    # ─── Build platform breakdown ─────────────────────────
    platform_breakdown: dict[str, int] = {}
    for msg in messages:
        platform_breakdown[msg.platform] = platform_breakdown.get(msg.platform, 0) + 1

    # ─── Count skipped (original lines minus parsed) ──────
    # Approximate: we can't know exactly since parser swallows skips
    skipped_count = 0

    return UploadResponse(
        messages=messages,
        total_count=len(messages),
        platform_breakdown=platform_breakdown,
        skipped_count=skipped_count,
        warnings=warnings,
    )
