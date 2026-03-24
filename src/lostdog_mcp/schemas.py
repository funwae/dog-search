from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field, HttpUrl


class MissingDogCase(BaseModel):
    title: str
    last_seen_at: datetime
    last_seen_location: str
    species: Literal["dog"] = "dog"
    breed_guess: str | None = None
    sex: Literal["female", "male", "unknown"] = "unknown"
    spayed_neutered: bool | None = None
    chip_status: Literal["chipped", "not_chipped", "unknown"] = "unknown"
    collar_status: Literal["wearing", "not_wearing", "unknown"] = "unknown"
    medical_notes: str | None = None
    owner_notes: str | None = None
    image_paths: list[str] = Field(default_factory=list)


class CandidateLead(BaseModel):
    title: str
    source_name: str
    source_url: HttpUrl | str
    snippet: str = ""
    location_text: str = ""
    found_at: datetime | None = None
    lat: float | None = None
    lng: float | None = None
    tags: list[str] = Field(default_factory=list)
    image_similarity: float = 0.0
    text_similarity: float = 0.0
    attribute_similarity: float = 0.0
    repost_penalty: float = 0.0


class ScoreBreakdown(BaseModel):
    text_score: float
    geo_score: float
    time_score: float
    attribute_score: float
    image_score: float
    repost_penalty: float
    final_score: float
    explanation: list[str]
