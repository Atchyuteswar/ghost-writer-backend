# routers/achievements.py

from fastapi import APIRouter, HTTPException
from models.schemas import UserStats, AchievementsResponse, StreakData
from services.achievement_service import (
    check_achievements,
    calculate_personality_stage,
    calculate_streak
)

router = APIRouter(prefix="/achievements", tags=["gamification"])

# In-memory store for demo. In production, this reads/writes to Supabase.
_user_stats_store: dict[str, UserStats] = {}

@router.post("/check")
async def check_user_achievements(stats: UserStats) -> AchievementsResponse:
    """
    Given the user's current stats, return their full achievement status,
    personality stage, and updated streak data.
    """
    achievements = check_achievements(stats)
    personality = calculate_personality_stage(stats.twin_accuracy)
    streak_update = calculate_streak(stats.last_active_date, stats.current_streak)

    streak_data = StreakData(
        current_streak=streak_update["current_streak"],
        best_streak=max(stats.best_streak, streak_update["current_streak"]),
        last_active_date=streak_update["last_active_date"],
        action=streak_update["action"]
    )

    return AchievementsResponse(
        achievements=achievements,
        unlocked_count=sum(1 for a in achievements if a.unlocked),
        total_count=len(achievements),
        personality_stage=personality,
        streak=streak_data
    )

@router.post("/increment")
async def increment_stat(stat_name: str, user_id: str = "default", amount: int = 1):
    """
    Increment a specific stat for a user.
    Call this from the frontend whenever a relevant action occurs.
    e.g. POST /achievements/increment?stat_name=total_ghost_writes
    """
    valid_stats = UserStats.model_fields.keys()
    if stat_name not in valid_stats:
        raise HTTPException(
            status_code=422,
            detail=f"Invalid stat name '{stat_name}'. Valid stats: {list(valid_stats)}"
        )

    if user_id not in _user_stats_store:
        _user_stats_store[user_id] = UserStats()

    current = _user_stats_store[user_id]
    current_val = getattr(current, stat_name)

    if isinstance(current_val, int):
        setattr(current, stat_name, current_val + amount)
    elif isinstance(current_val, float):
        setattr(current, stat_name, round(current_val + amount, 2))

    return {
        "stat": stat_name,
        "previous_value": current_val,
        "new_value": getattr(current, stat_name),
        "user_id": user_id
    }

@router.get("/stats/{user_id}")
async def get_user_stats(user_id: str) -> UserStats:
    """Get current stats for a user."""
    if user_id not in _user_stats_store:
        _user_stats_store[user_id] = UserStats()
    return _user_stats_store[user_id]

@router.put("/stats/{user_id}")
async def update_user_stats(user_id: str, stats: UserStats) -> UserStats:
    """Replace stats for a user (used for syncing from Supabase)."""
    _user_stats_store[user_id] = stats
    return stats