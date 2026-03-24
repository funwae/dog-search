"""Shared test fixtures."""

from __future__ import annotations

import pytest

from lostdog_mcp.storage.db import get_engine, reset_engine
from lostdog_mcp.storage.models import CaseRow, CandidateRow  # noqa: F401 — register tables

from sqlmodel import SQLModel, Session


@pytest.fixture()
def db_session(tmp_path):
    """Provide an in-memory SQLite session for each test."""
    reset_engine()
    db_url = f"sqlite:///{tmp_path / 'test.db'}"
    engine = get_engine(db_url)
    with Session(engine) as session:
        yield session
    reset_engine()
