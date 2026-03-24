"""SQLModel ORM models for LostDog persistence."""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlmodel import Field, SQLModel


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return uuid.uuid4().hex[:12]


class CaseRow(SQLModel, table=True):
    __tablename__ = "cases"

    id: str = Field(default_factory=_new_id, primary_key=True)
    title: str
    last_seen_at: datetime
    last_seen_location: str
    last_seen_lat: Optional[float] = None
    last_seen_lng: Optional[float] = None
    species: str = "dog"
    breed_guess: Optional[str] = None
    sex: str = "unknown"
    spayed_neutered: Optional[bool] = None
    chip_status: str = "unknown"
    collar_status: str = "unknown"
    medical_notes: Optional[str] = None
    owner_notes: Optional[str] = None
    image_paths_json: str = "[]"
    status: str = "active"
    created_at: datetime = Field(default_factory=_utcnow)
    updated_at: datetime = Field(default_factory=_utcnow)


class CandidateRow(SQLModel, table=True):
    __tablename__ = "candidates"

    id: str = Field(default_factory=_new_id, primary_key=True)
    case_id: str = Field(index=True)
    title: str
    source_name: str
    source_url: str
    snippet: str = ""
    location_text: str = ""
    found_at: Optional[datetime] = None
    lat: Optional[float] = None
    lng: Optional[float] = None
    tags_json: str = "[]"
    image_similarity: float = 0.0
    text_similarity: float = 0.0
    attribute_similarity: float = 0.0
    repost_penalty: float = 0.0
    final_score: float = 0.0
    explanation_json: str = "[]"
    status: str = "new"
    operator_notes: Optional[str] = None
    created_at: datetime = Field(default_factory=_utcnow)
    content_hash: Optional[str] = None
