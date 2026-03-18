"""Ghost-Writer Backend — Battles Router.

POST /battles/generate — Generate two AI responses for a twin battle.
GET  /battles/prompts  — Get example battle prompts.
"""
import asyncio
from fastapi import APIRouter, HTTPException

from models.schemas import BattleGenerateRequest, BattleGenerateResponse
from services.generator import TwinGenerator, VALID_PERSONALITY_TYPES

router = APIRouter()
generator = TwinGenerator()

BATTLE_PROMPTS = [
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


@router.post("/generate", response_model=BattleGenerateResponse)
async def generate_battle(request: BattleGenerateRequest):
    """Generate two distinct AI responses for a battle prompt."""
    if not request.prompt.strip():
        raise HTTPException(status_code=422, detail="Battle prompt cannot be empty.")

    for name, player in [("player1", request.player1), ("player2", request.player2)]:
        if player.personality_type not in VALID_PERSONALITY_TYPES:
            raise HTTPException(
                status_code=422,
                detail=f"Invalid personality_type for {name}. Must be one of: {VALID_PERSONALITY_TYPES}",
            )

    # Run both generations in parallel
    loop = asyncio.get_event_loop()
    result_1, result_2 = await asyncio.gather(
        loop.run_in_executor(None, lambda: generator.generate(
            prompt=request.prompt,
            vibe_level=request.player1.vibe_level,
            personality_type=request.player1.personality_type,
        )),
        loop.run_in_executor(None, lambda: generator.generate(
            prompt=request.prompt,
            vibe_level=request.player2.vibe_level,
            personality_type=request.player2.personality_type,
        )),
    )

    return BattleGenerateResponse(
        prompt=request.prompt,
        response_1=result_1["response"],
        response_2=result_2["response"],
        match_1=result_1["match_percent"],
        match_2=result_2["match_percent"],
        player1_name=request.player1.name,
        player2_name=request.player2.name,
    )


@router.get("/prompts")
async def get_battle_prompts():
    """Get a list of example battle prompts."""
    return BATTLE_PROMPTS
