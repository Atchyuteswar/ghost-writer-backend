"""Ghost-Writer Backend — PII Router.

POST /pii/mask — Mask PII in messages.
GET  /pii/status — Check Presidio readiness status.
"""
from fastapi import APIRouter, HTTPException

from models.schemas import MaskPIIRequest, MaskPIIResponse
from services.pii_masker import PIIMasker

router = APIRouter()
masker = PIIMasker()


@router.post("/mask", response_model=MaskPIIResponse)
async def mask_pii(request: MaskPIIRequest):
    """Mask PII in messages based on provided settings."""
    if not request.messages:
        raise HTTPException(status_code=422, detail="No messages to process.")

    masked_messages, masked_count, breakdown = masker.mask(
        request.messages, request.settings
    )

    return MaskPIIResponse(
        messages=masked_messages,
        masked_count=masked_count,
        mask_breakdown=breakdown,
    )


@router.get("/status")
async def pii_status():
    """Check if Presidio and spaCy are loaded and ready."""
    supported = [
        "PHONE_NUMBER", "EMAIL_ADDRESS", "PERSON",
        "LOCATION", "GPE", "MONEY", "CREDIT_CARD",
    ]
    return {
        "presidio_loaded": masker.is_available,
        "spacy_model": "en_core_web_lg",
        "supported_entities": supported,
    }
