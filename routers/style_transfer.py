"""Ghost-Writer Backend — Style Transfer Router.

POST /style-transfer — Rewrite text in the user's voice with a specific style.
"""
from fastapi import APIRouter, HTTPException

from models.schemas import StyleTransferRequest, StyleTransferResponse
from services.generator import TwinGenerator, VALID_PERSONALITY_TYPES

router = APIRouter()
generator = TwinGenerator()


@router.post("", response_model=StyleTransferResponse)
async def style_transfer(request: StyleTransferRequest):
    """Transform text into the user's voice with a chosen style."""
    if request.personality_type not in VALID_PERSONALITY_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid personality_type. Must be one of: {VALID_PERSONALITY_TYPES}",
        )

    result = generator.style_transfer(
        source_text=request.source_text,
        vibe_level=request.vibe_level,
        personality_type=request.personality_type,
        style=request.style,
    )

    return StyleTransferResponse(**result)
