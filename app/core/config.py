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

    # Generation provider timeout/retry/backoff
    GENERATION_TIMEOUT_SECONDS: float = 60.0  # Max seconds per Gemini call
    GENERATION_MAX_RETRIES: int = 3  # Max retry attempts on transient errors
    GENERATION_RETRY_BASE_DELAY: float = 1.0  # Initial backoff delay in seconds
    GENERATION_RETRY_MAX_DELAY: float = 30.0  # Maximum backoff delay cap in seconds

    # Adaptive fanout controls
    GENERATION_CANDIDATE_MIN: int = 1  # Minimum allowed parallel candidates
    GENERATION_CANDIDATE_MAX: int = 4  # Maximum allowed parallel candidates

    # Security Settings
    API_AUTH_KEY: str = ""  # Required for API access in production
    ALLOWED_ORIGINS: str = "*"  # Comma-separated list of allowed CORS origins
    MAX_CONTENT_LENGTH: int = 16 * 1024 * 1024  # 16MB max upload size

    # Database Settings
    DATABASE_URL: str = ""  # Optional: override Supabase connection

    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"


settings = Settings()
