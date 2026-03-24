from __future__ import annotations

from datetime import datetime

from lostdog_mcp.schemas import MissingDogCase


def test_case_schema_accepts_minimum_fields() -> None:
    case = MissingDogCase(
        title="Missing dog",
        last_seen_at=datetime(2025, 6, 26, 12, 0, 0),
        last_seen_location="Conroe, TX",
    )
    assert case.species == "dog"
    assert case.sex == "unknown"
    assert case.image_paths == []
