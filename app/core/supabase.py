"""Supabase client configuration."""

from supabase import create_client, Client
from app.core.config import settings


# Supabase configuration from environment
SUPABASE_URL: str = settings.SUPABASE_PROJECT_URL
SUPABASE_KEY: str = settings.SUPABASE_PUBLISHABLE_KEY

# Lazy-initialized client instance
_supabase_client: Client | None = None


def get_supabase() -> Client:
    """
    Get or create the Supabase client instance.
    
    Returns:
        Configured Supabase client
    """
    global _supabase_client
    
    if _supabase_client is None:
        if not SUPABASE_URL or not SUPABASE_KEY:
            raise ValueError(
                "Supabase URL and key must be configured. "
                "Set SUPABASE_PROJECT_URL and SUPABASE_PUBLISHABLE_KEY in .env"
            )
        _supabase_client = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    return _supabase_client


def reset_supabase_client() -> None:
    """Reset the Supabase client (useful for testing)."""
    global _supabase_client
    _supabase_client = None
