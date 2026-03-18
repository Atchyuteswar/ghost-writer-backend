"""Ghost-Writer Backend — Configuration.

Reads all settings from .env file using pydantic-settings.
"""
from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    ANTHROPIC_API_KEY: str = ""
    PINECONE_API_KEY: str = ""
    PINECONE_INDEX_NAME: str = "ghost-writer-memories"
    PINECONE_ENVIRONMENT: str = "us-east-1-aws"
    SUPABASE_URL: str = "https://kpeslowdqajzlmhlwajm.supabase.co"
    SUPABASE_KEY: str = ""
    LOCAL_ONLY_MODE: bool = True
    MAX_FILE_SIZE_MB: int = 50
    CORS_ORIGINS: List[str] = ["http://localhost:3000", "http://localhost:8081", "*"]
    ELEVENLABS_API_KEY: str = ""
    PORT: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": True,
    }


settings = Settings()
