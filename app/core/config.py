"""Application configuration."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    PROJECT_NAME: str = "ArchAI BOM"
    VERSION: str = "0.1.0"
    DEBUG: bool = False

    # API Settings
    API_V1_PREFIX: str = "/api/v1"

    # Supabase Settings
    SUPABASE_PROJECT_URL: str = ""
    SUPABASE_PUBLISHABLE_KEY: str = ""
    SUPABASE_PASSWORD: str = ""

    # Flask Settings
    SECRET_KEY: str = ""  # Set in production for session security

    # Google AI Settings
    GOOGLE_API_KEY: str = ""

    # Generation pipeline concurrency
    GENERATION_PARALLEL_CANDIDATES: int = 2
    GENERATION_MAX_WORKERS: int = 4

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
