"""Ghost-Writer Backend — Analyze Router.

POST /analyze — Runs NLP analysis on parsed messages.
"""
import time
import logging
from datetime import datetime
from fastapi import APIRouter, HTTPException, Response

from models.schemas import (
    AnalyzeRequest, AnalyzeResponse,
    SocialMapResponse, SentimentHistoryResponse,
    ChaosLogRequest, ChaosLogResponse
)
from services.nlp import NLPAnalyzer
from services.generator import TwinGenerator
from services.db import (
    upsert_social_map, 
    upsert_sentiment_history, 
    save_chaos_log
)

router = APIRouter()
logger = logging.getLogger(__name__)
analyzer = NLPAnalyzer()
generator = TwinGenerator()


@router.post("", response_model=AnalyzeResponse)
async def analyze_messages(request: AnalyzeRequest, response: Response):
    """Run full NLP analysis on a set of parsed messages."""
    if not request.messages:
        raise HTTPException(
            status_code=422,
            detail="No messages to analyze. Please upload files first.",
        )

    start = time.time()
    result = analyzer.analyze(request.messages)
    elapsed_ms = round((time.time() - start) * 1000, 1)

    response.headers["X-Processing-Time"] = f"{elapsed_ms}ms"
    return result


@router.post("/social", response_model=SocialMapResponse)
async def analyze_social(request: AnalyzeRequest):
    """Analyze message distribution and style per contact."""
    if not request.messages:
        return SocialMapResponse(contacts=[])
    
    result = analyzer.analyze_social(request.messages)
    
    if request.user_id:
        upsert_social_map(request.user_id, result.contacts)
        
    return result


@router.post("/sentiment-history", response_model=SentimentHistoryResponse)
async def analyze_sentiment_history(request: AnalyzeRequest):
    """Analyze daily sentiment trends."""
    if not request.messages:
        return SentimentHistoryResponse(days=[], avg_score=0.0)
    
    result = analyzer.analyze_sentiment(request.messages)
    
    if request.user_id:
        upsert_sentiment_history(request.user_id, result.days)
        
    return result


@router.post("/chaos-log", response_model=ChaosLogResponse)
async def generate_chaos_log(request: ChaosLogRequest):
    """Generate a daily summary log in the user's voice."""
    date = request.date or datetime.now().strftime("%Y-%m-%d")
    
    # Use vibe level from request if possible, or default
    vibe_level = 75 # Default to chaotic for chaos log
    personality = "chaotic-creative"
    
    message_texts = [m.text for m in request.messages]
    result = generator.generate_chaos_log(date, message_texts, vibe_level, personality)
    
    if request.user_id:
        save_chaos_log(request.user_id, result["content"], result["date"], result["source_stats"])
        
    return ChaosLogResponse(**result)
