# services/achievement_service.py

from datetime import datetime, date, timedelta
from models.schemas import (
    Achievement, AchievementStatus, StreakData, UserStats
)

# Master list of all achievements with their unlock conditions
ACHIEVEMENTS_REGISTRY = [
    {
        "id": "first_ghost_write",
        "name": "First Ghost-Write",
        "description": "Sent your first AI-written message",
        "icon": "edit_note",
        "accent_color": "#C8FF57",
        "condition_field": "total_ghost_writes",
        "condition_value": 1
    },
    {
        "id": "seven_day_streak",
        "name": "7-Day Streak",
        "description": "Used Ghost-Writer 7 days in a row",
        "icon": "local_fire_department",
        "accent_color": "#FBBF24",
        "condition_field": "current_streak",
        "condition_value": 7
    },
    {
        "id": "memory_keeper",
        "name": "Memory Keeper",
        "description": "Loaded 500+ memories into your twin",
        "icon": "auto_stories",
        "accent_color": "#A78BFA",
        "condition_field": "total_memories",
        "condition_value": 500
    },
    {
        "id": "style_master",
        "name": "Style Master",
        "description": "Used Style Transfer 5 times",
        "icon": "magic_button",
        "accent_color": "#22D3EE",
        "condition_field": "total_style_transfers",
        "condition_value": 5
    },
    {
        "id": "accuracy_90",
        "name": "Twin Accuracy 90%",
        "description": "Reached 90% twin match accuracy",
        "icon": "verified",
        "accent_color": "#C8FF57",
        "condition_field": "twin_accuracy",
        "condition_value": 90
    },
    {
        "id": "night_owl",
        "name": "Night Owl",
        "description": "Set vibe to 100% for the first time",
        "icon": "nights_stay",
        "accent_color": "#F472B6",
        "condition_field": "max_vibe_reached",
        "condition_value": 100
    },
    {
        "id": "battle_warrior",
        "name": "Battle Warrior",
        "description": "Won your first Twin Battle",
        "icon": "sports_mma",
        "accent_color": "#A78BFA",
        "condition_field": "battle_wins",
        "condition_value": 1
    },
    {
        "id": "memory_lane",
        "name": "Memory Lane",
        "description": "Opened 10 Memory Lane notifications",
        "icon": "auto_awesome",
        "accent_color": "#FBBF24",
        "condition_field": "memory_lane_opens",
        "condition_value": 10
    },
    {
        "id": "chaos_logger",
        "name": "Chaos Logger",
        "description": "Written 7 journal entries",
        "icon": "book",
        "accent_color": "#A78BFA",
        "condition_field": "total_journal_entries",
        "condition_value": 7
    },
    {
        "id": "thirty_day_streak",
        "name": "Month Strong",
        "description": "30-day streak achieved",
        "icon": "calendar_month",
        "accent_color": "#FBBF24",
        "condition_field": "current_streak",
        "condition_value": 30
    }
]

def check_achievements(stats: "UserStats") -> list["AchievementStatus"]:
    """
    Given a UserStats object, check which achievements
    are unlocked and which are still locked.
    Returns a list of AchievementStatus objects.
    """
    results = []
    stats_dict = stats.model_dump()

    for achievement in ACHIEVEMENTS_REGISTRY:
        field = achievement["condition_field"]
        required = achievement["condition_value"]
        current_value = stats_dict.get(field, 0)
        is_unlocked = current_value >= required

        results.append(AchievementStatus(
            id=achievement["id"],
            name=achievement["name"],
            description=achievement["description"],
            icon=achievement["icon"],
            accent_color=achievement["accent_color"],
            unlocked=is_unlocked,
            progress_current=min(current_value, required),
            progress_required=required,
            progress_percent=min(round((current_value / required) * 100), 100)
        ))

    return results

def calculate_personality_stage(twin_accuracy: float) -> dict:
    """Calculate the user's personality evolution stage."""
    stages = [
        {"name": "Rookie", "min": 0, "max": 30},
        {"name": "Regular", "min": 30, "max": 61},
        {"name": "Power User", "min": 61, "max": 86},
        {"name": "Legend", "min": 86, "max": 101}
    ]
    current_stage_index = 0
    for i, stage in enumerate(stages):
        if stage["min"] <= twin_accuracy < stage["max"]:
            current_stage_index = i
            break

    current_stage = stages[current_stage_index]
    next_stage = stages[current_stage_index + 1] if current_stage_index < len(stages) - 1 else None

    progress_in_stage = twin_accuracy - current_stage["min"]
    stage_range = current_stage["max"] - current_stage["min"]
    progress_percent = round((progress_in_stage / stage_range) * 100)

    return {
        "current_stage": current_stage["name"],
        "current_stage_index": current_stage_index,
        "total_stages": len(stages),
        "progress_percent": progress_percent,
        "next_stage": next_stage["name"] if next_stage else None,
        "stages": [s["name"] for s in stages]
    }

def calculate_streak(last_active_date: str | None, current_streak: int) -> dict:
    """
    Given the last active date string and current streak count,
    determine if the streak should increment, stay, or reset.
    Returns updated streak data.
    """
    today = date.today()

    if last_active_date is None:
        return {
            "current_streak": 1,
            "last_active_date": today.isoformat(),
            "action": "started"
        }

    last_active = date.fromisoformat(last_active_date)
    delta = (today - last_active).days

    if delta == 0:
        # Same day, no change
        return {
            "current_streak": current_streak,
            "last_active_date": last_active_date,
            "action": "same_day"
        }
    elif delta == 1:
        # Consecutive day, increment
        return {
            "current_streak": current_streak + 1,
            "last_active_date": today.isoformat(),
            "action": "incremented"
        }
    else:
        # Gap in streak, reset
        return {
            "current_streak": 1,
            "last_active_date": today.isoformat(),
            "action": "reset"
        }