# routers/voice_studio.py

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from services.voice_service import VoiceService
import base64

router = APIRouter(prefix="/voice", tags=["voice-studio"])
voice_service = VoiceService()

class SynthesizeRequest(BaseModel):
    text: str = Field(min_length=1, max_length=1000)
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
    stability: float = Field(default=0.5, ge=0.0, le=1.0)
    similarity_boost: float = Field(default=0.75, ge=0.0, le=1.0)
    return_base64: bool = False  # if True, return base64 string instead of raw bytes

class SynthesizeResponse(BaseModel):
    audio_base64: str
    duration_estimate_seconds: float
    provider: str

@router.post("/synthesize")
async def synthesize_speech(request: SynthesizeRequest):
    """
    Convert text to speech in the user's twin voice.
    Returns MP3 audio. If return_base64 is True, returns JSON with base64.
    Otherwise streams raw MP3 bytes.
    """
    try:
        audio_bytes = await voice_service.synthesize_text(
            text=request.text,
            voice_id=request.voice_id,
            stability=request.stability,
            similarity_boost=request.similarity_boost
        )
    except Exception as e:
        raise HTTPException(
            status_code=503,
            detail=f"Voice synthesis failed: {str(e)}. Make sure ELEVENLABS_API_KEY is set or gTTS is installed."
        )

    if request.return_base64:
        # React Native can't directly play streamed audio easily,
        # so base64 is more convenient for mobile
        audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
        word_count = len(request.text.split())
        duration_estimate = word_count / 2.5  # rough estimate: 2.5 words per second
        provider = "elevenlabs" if voice_service.use_elevenlabs else "gtts"
        return SynthesizeResponse(
            audio_base64=audio_b64,
            duration_estimate_seconds=round(duration_estimate, 1),
            provider=provider
        )
    else:
        return Response(
            content=audio_bytes,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=twin_voice.mp3"}
        )

@router.get("/voices")
async def list_voices():
    """List all available voices."""
    voices = await voice_service.get_available_voices()
    return {"voices": voices, "provider": "elevenlabs" if voice_service.use_elevenlabs else "gtts"}

@router.post("/synthesize-twin-response")
async def synthesize_twin_response(
    prompt: str,
    vibe_level: int = 72,
    personality_type: str = "chaotic-creative",
    voice_id: str = "21m00Tcm4TlvDq8ikWAM"
):
    """
    Generate a twin text response AND synthesize it to audio in one call.
    This is the main endpoint the Voice Studio screen uses.
    """
    from services.generator import TwinGenerator
    from models.schemas import GenerateRequest

    # Step 1: Generate twin text response
    generator = TwinGenerator()
    gen_request = GenerateRequest(
        prompt=prompt,
        vibe_level=vibe_level,
        personality_type=personality_type
    )
    gen_response = generator.generate(gen_request)

    # Step 2: Synthesize the generated text to audio
    try:
        audio_bytes = await voice_service.synthesize_text(
            text=gen_response.response,
            voice_id=voice_id
        )
    except Exception as e:
        # Return text response even if voice fails
        return {
            "text_response": gen_response.response,
            "match_percent": gen_response.match_percent,
            "audio_base64": None,
            "error": f"Voice synthesis failed: {str(e)}"
        }

    audio_b64 = base64.b64encode(audio_bytes).decode('utf-8')
    return {
        "text_response": gen_response.response,
        "match_percent": gen_response.match_percent,
        "audio_base64": audio_b64,
        "provider": "elevenlabs" if voice_service.use_elevenlabs else "gtts"
    }

