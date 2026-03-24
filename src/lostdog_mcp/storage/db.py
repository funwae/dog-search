"""SQLite database engine and session management."""

from __future__ import annotations

from sqlmodel import Session, SQLModel, create_engine

_engine = None


def get_engine(db_url: str = "sqlite:///./lostdog.db"):
    global _engine
    if _engine is None:
        _engine = create_engine(db_url, echo=False)
        SQLModel.metadata.create_all(_engine)
    return _engine


def reset_engine() -> None:
    """Reset the global engine (useful for tests)."""
    global _engine
    _engine = None


def get_session(db_url: str = "sqlite:///./lostdog.db") -> Session:
    return Session(get_engine(db_url))
