"""Ghost-Writer Backend — Pydantic Schemas.

All request and response models for every endpoint.
"""
from pydantic import BaseModel, Field
from typing import Optional


# ─── Parsed Message ────────────────────────────────────────────

class ParsedMessage(BaseModel):
    id: str
    timestamp: str
    sender: str
    text: str
    platform: str
    word_count: int
    char_count: int


# ─── Upload ────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    messages: list[ParsedMessage]
    total_count: int
    platform_breakdown: dict[str, int]
    skipped_count: int
    warnings: list[str]


# ─── Analyze ───────────────────────────────────────────────────

class WordFrequency(BaseModel):
    word: str
    count: int
    frequency: float


class AnalyzeRequest(BaseModel):
    messages: list[ParsedMessage]
    user_id: Optional[str] = None


class AnalyzeResponse(BaseModel):
    total_messages: int
    avg_sentiment: float
    sentiment_by_day: dict[str, float]
    sentiment_by_hour: dict[int, float]
    vocabulary_richness: float
    avg_message_length: float
    avg_word_count: float
    slang_frequency: float
    top_words: list[WordFrequency]
    top_slang: list[WordFrequency]
    platform_stats: dict[str, int]
    most_active_hour: int
    most_active_day: str


class SocialContact(BaseModel):
    name: str
    message_count: int
    avg_sentiment: float
    top_words: list[str]
    style_description: str


class SocialMapResponse(BaseModel):
    contacts: list[SocialContact]


class SentimentDay(BaseModel):
    date: str
    score: float
    mood_tag: str
    message_count: int
    excerpts: list[str]


class SentimentHistoryResponse(BaseModel):
    days: list[SentimentDay]
    avg_score: float


class ChaosLogRequest(BaseModel):
    messages: list[ParsedMessage]
    date: Optional[str] = None
    user_id: Optional[str] = None


class ChaosLogResponse(BaseModel):
    content: str
    date: str
    source_stats: dict[str, int]


# ─── PII ───────────────────────────────────────────────────────

class PIISettings(BaseModel):
    mask_phone_numbers: bool = True
    mask_email_addresses: bool = True
    mask_real_names: bool = False
    mask_locations: bool = True
    mask_financial_info: bool = True


class MaskPIIRequest(BaseModel):
    messages: list[ParsedMessage]
    settings: PIISettings


class MaskPIIResponse(BaseModel):
    messages: list[ParsedMessage]
    masked_count: int
    mask_breakdown: dict[str, int]


# ─── Generate ──────────────────────────────────────────────────

class GenerateRequest(BaseModel):
    prompt: str
    vibe_level: int = Field(ge=0, le=100)
    personality_type: str
    context_messages: list[str] = []


class GenerateResponse(BaseModel):
    response: str
    match_percent: float
    vibe_applied: int
    tokens_used: int


# ─── Style Transfer ───────────────────────────────────────────

class StyleTransferRequest(BaseModel):
    source_text: str = Field(min_length=1, max_length=5000)
    vibe_level: int = Field(ge=0, le=100)
    style: str = Field(pattern="^(executive|persuasive|casual|academic)$")
    personality_type: str


class StyleTransferResponse(BaseModel):
    transformed_text: str
    vibe_match: float
    original_length: int
    transformed_length: int
    style_applied: str


# ─── Memories ──────────────────────────────────────────────────

class MemoryResult(BaseModel):
    text: str
    score: float
    date: str
    platform: str


class MemorySearchRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=20)


class MemorySearchResponse(BaseModel):
    results: list[MemoryResult]
    query_used: str


class StoreMemoriesRequest(BaseModel):
    messages: list[ParsedMessage]
    user_id: Optional[str] = None


# ─── Battles ──────────────────────────────────────────────────

class BattlePlayer(BaseModel):
    vibe_level: int = Field(ge=0, le=100)
    personality_type: str
    name: str


class BattleGenerateRequest(BaseModel):
    prompt: str
    player1: BattlePlayer
    player2: BattlePlayer


class BattleGenerateResponse(BaseModel):
    prompt: str
    response_1: str
    response_2: str
    match_1: float
    match_2: float
    player1_name: str
    player2_name: str

class UserStats(BaseModel):
    total_ghost_writes: int = 0
    current_streak: int = 0
    best_streak: int = 0
    last_active_date: str | None = None
    total_memories: int = 0
    total_style_transfers: int = 0
    twin_accuracy: float = 0.0
    max_vibe_reached: int = 0
    battle_wins: int = 0
    battle_losses: int = 0
    memory_lane_opens: int = 0
    total_journal_entries: int = 0

class AchievementStatus(BaseModel):
    id: str
    name: str
    description: str
    icon: str
    accent_color: str
    unlocked: bool
    progress_current: int
    progress_required: int
    progress_percent: int

class StreakData(BaseModel):
    current_streak: int
    best_streak: int
    last_active_date: str | None
    action: str  # "incremented" | "same_day" | "reset" | "started"

class AchievementsResponse(BaseModel):
    achievements: list[AchievementStatus]
    unlocked_count: int
    total_count: int
    personality_stage: dict
    streak: StreakData

class Achievement(BaseModel):
    id: str
    user_id: str
    achievement_type: str
    unlocked_at: Optional[str] = None
    progress: int = 0
    created_at: Optional[str] = None
