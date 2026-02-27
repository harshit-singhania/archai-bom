"""Database session management for SQLModel."""

from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlmodel import Session, SQLModel

from app.core.config import settings


# Database engine (initialized lazily)
_engine = None
_session_maker = None


def get_database_url() -> str:
    """Get database URL from settings or Supabase configuration."""
    # If DATABASE_URL is explicitly set, use it
    if hasattr(settings, "DATABASE_URL") and settings.DATABASE_URL:
        return settings.DATABASE_URL

    # Otherwise, construct from Supabase credentials
    if not settings.SUPABASE_PROJECT_URL or not settings.SUPABASE_PASSWORD:
        raise ValueError(
            "Database configuration incomplete. "
            "Set either DATABASE_URL or both SUPABASE_PROJECT_URL and SUPABASE_PASSWORD."
        )

    project_url = settings.SUPABASE_PROJECT_URL.strip()
    project_ref = (
        project_url.replace("https://", "")
        .replace(".supabase.co", "")
        .replace("/", "")
        .strip()
    )

    return f"postgresql://postgres:{settings.SUPABASE_PASSWORD}@db.{project_ref}.supabase.co:5432/postgres"


def get_engine():
    """Get or create the database engine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _engine = create_engine(database_url, echo=settings.DEBUG)
    return _engine


def get_session_maker():
    """Get or create the session maker."""
    global _session_maker
    if _session_maker is None:
        _session_maker = sessionmaker(
            autocommit=False, autoflush=False, bind=get_engine(), class_=Session
        )
    return _session_maker


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Get a database session with automatic cleanup.

    Usage:
        with get_session() as session:
            result = session.exec(select(Model)).all()
    """
    session = get_session_maker()()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def create_tables():
    """Create all database tables."""
    SQLModel.metadata.create_all(get_engine())


def reset_engine():
    """Reset the database engine (useful for testing)."""
    global _engine, _session_maker
    _engine = None
    _session_maker = None
