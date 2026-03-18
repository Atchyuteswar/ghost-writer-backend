"""Ghost-Writer Backend — Generate Router.

POST /generate — Generate AI response in user's voice.
GET  /generate/prompts — Get example prompts.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from models.schemas import GenerateRequest, GenerateResponse
from services.generator import TwinGenerator, VALID_PERSONALITY_TYPES

router = APIRouter()
generator = TwinGenerator()

EXAMPLE_PROMPTS = [
    "Explain why your city is the best city in the world",
    "Describe your perfect Sunday in detail",
    "Give your honest opinion on pineapple on pizza",
    "What would you do if you won 10 crore rupees tomorrow",
    "Explain what friendship means to you",
    "Describe your most embarrassing moment without cringing",
    "What is your hottest controversial take",
    "Explain why your favorite food is objectively the best food",
    "Describe how you would survive a zombie apocalypse",
    "What is one thing you would change about yourself and why",
]


@router.post("", response_model=GenerateResponse)
async def generate_response(request: GenerateRequest):
    """Generate an AI response in the user's voice."""
    if not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Prompt cannot be empty.")

    if request.personality_type not in VALID_PERSONALITY_TYPES:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid personality_type. Must be one of: {VALID_PERSONALITY_TYPES}",
        )

    result = generator.generate(
        prompt=request.prompt,
        vibe_level=request.vibe_level,
        personality_type=request.personality_type,
        context_messages=request.context_messages,
    )

    return GenerateResponse(**result)


@router.get("/prompts")
async def get_prompts():
    """Get a list of example battle/chat prompts."""
    return EXAMPLE_PROMPTS

class ChaosLogRequest(BaseModel):
    vibe_level: int = Field(default=72, ge=0, le=100)
    personality_type: str = "chaotic-creative"
    date_str: str  # "2025-03-18"
    message_count: int = 0        # how many messages they sent that day
    top_words: list[str] = []     # their most used words today
    avg_sentiment: float = 0.3    # their mood score for the day

@router.post("/chaos-log/generate")
async def generate_chaos_log_entry(request: ChaosLogRequest) -> GenerateResponse:
    """
    Auto-generate a journal entry for the given date,
    written in the user's twin voice at their vibe level.
    """
    # Build a rich prompt that gives Claude enough context
    mood_label = (
        "great" if request.avg_sentiment > 0.5 else
        "good" if request.avg_sentiment > 0.2 else
        "neutral" if request.avg_sentiment > -0.2 else
        "rough"
    )
    top_words_str = ", ".join(request.top_words[:5]) if request.top_words else "the usual stuff"

    prompt = f"""Write a personal journal entry for {request.date_str}.

Context about this person's day:
- They sent {request.message_count} messages
- Their mood was {mood_label} (sentiment score: {request.avg_sentiment:.2f})
- Their most used words today: {top_words_str}

Write 3-4 sentences as a journal entry in first person.
Make it feel authentic and personal, not generic.
Reference the mood and activities naturally without being too on-the-nose.
Do NOT start with "Dear diary". Just write naturally."""

    generator = TwinGenerator()
    result = generator.generate(
        prompt=prompt,
        vibe_level=request.vibe_level,
        personality_type=request.personality_type
    )
    return GenerateResponse(**result)