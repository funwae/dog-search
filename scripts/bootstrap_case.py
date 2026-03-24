from __future__ import annotations

from datetime import datetime

from lostdog_mcp.schemas import MissingDogCase

case = MissingDogCase(
    title="Missing black tri fluffy corgi",
    last_seen_at=datetime(2025, 6, 26, 18, 0, 0),
    last_seen_location="South Rayburn Drive in Conroe, Texas",
    breed_guess="black tri fluffy corgi",
    sex="female",
    chip_status="chipped",
    collar_status="not_wearing",
    medical_notes="allergies and special food",
    owner_notes="needs medicine and quick follow-up",
)

print(case.model_dump_json(indent=2))
