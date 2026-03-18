"""Ghost-Writer Backend — Database Service (Supabase).

Provides a centralized Supabase client for backend data persistence.
"""
import logging
from supabase import create_client, Client
from config import settings

logger = logging.getLogger(__name__)

# Initialize global Supabase client
_supabase: Client = None

def get_db() -> Client:
    """Get the Supabase client instance."""
    global _supabase
    if _supabase is None:
        try:
            if not settings.SUPABASE_URL or not settings.SUPABASE_KEY:
                logger.warning("Supabase credentials missing in config. Database features may be limited.")
                return None
            
            _supabase = create_client(settings.SUPABASE_URL, settings.SUPABASE_KEY)
            logger.info("Supabase client initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase client: {e}")
            return None
    
    return _supabase

# Export a default instance
db: Client = get_db()


def save_chaos_log(user_id: str, content: str, date: str, source_stats: dict):
    """Save a daily chaos log to Supabase."""
    client = get_db()
    if not client: return
    
    try:
        client.from_("chaos_logs").upsert({
            "user_id": user_id,
            "content": content,
            "date": date,
            "source_stats": source_stats
        }, on_conflict="user_id,date").execute()
    except Exception as e:
        logger.error(f"Error saving chaos log: {e}")


def upsert_insights_detail(user_id: str, field: str, data: any):
    """Upsert detailed insight fields (social_map, mood_history)."""
    client = get_db()
    if not client: return
    
    try:
        # Check if row exists
        existing = client.from_("insights").select("*").eq("user_id", user_id).execute()
        if existing.data:
            client.from_("insights").update({field: data}).eq("user_id", user_id).execute()
        else:
            client.from_("insights").insert({"user_id": user_id, field: data}).execute()
    except Exception as e:
        logger.error(f"Error upserting insights detail ({field}): {e}")


def update_achievement(user_id: str, achievement_type: str, progress: int = 100):
    """Update or unlock an achievement."""
    client = get_db()
    if not client: return
    
    try:
        client.from_("achievements").upsert({
            "user_id": user_id,
            "achievement_type": achievement_type,
            "progress": progress,
            "unlocked_at": "now()" if progress >= 100 else None
        }, on_conflict="user_id,achievement_type").execute()
    except Exception as e:
        logger.error(f"Error updating achievement: {e}")


def upsert_social_map(user_id: str, contacts: list):
    """Save social contacts list to insights table."""
    upsert_insights_detail(user_id, "social_map", [c.model_dump() if hasattr(c, "model_dump") else c for c in contacts])


def upsert_sentiment_history(user_id: str, days: list):
    """Save sentiment history list to insights table."""
    upsert_insights_detail(user_id, "sentiment_history", [d.model_dump() if hasattr(d, "model_dump") else d for d in days])
