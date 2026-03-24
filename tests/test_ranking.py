from __future__ import annotations

from datetime import datetime, timedelta

from lostdog_mcp.ranking import score_candidate
from lostdog_mcp.schemas import CandidateLead, MissingDogCase


def build_case() -> MissingDogCase:
    return MissingDogCase(
        title="Missing black tri fluffy corgi",
        last_seen_at=datetime(2025, 6, 26, 18, 0, 0),
        last_seen_location="South Rayburn Drive in Conroe Texas near Highway 242",
        breed_guess="black tri fluffy corgi",
        sex="female",
        spayed_neutered=True,
        chip_status="chipped",
        collar_status="not_wearing",
        medical_notes="allergies and special food",
        owner_notes="needs medicine",
        image_paths=[],
    )


def test_high_quality_candidate_scores_well() -> None:
    case = build_case()
    candidate = CandidateLead(
        title="Found female corgi near Rayburn and 242",
        source_name="public_web",
        source_url="https://example.com/found-dog",
        snippet="Black tri fluffy corgi found with no collar in Conroe.",
        location_text="Conroe TX near South Rayburn",
        found_at=case.last_seen_at + timedelta(hours=12),
        lat=30.315,
        lng=-95.454,
        tags=["female", "corgi", "black", "tri", "fluffy", "chip", "no_collar"],
        image_similarity=0.84,
        repost_penalty=0.0,
    )

    result = score_candidate(case, candidate, last_seen_lat=30.314, last_seen_lng=-95.455)
    assert result.final_score > 0.65
    assert any("Image similarity" in line for line in result.explanation)


def test_repost_penalty_pushes_echo_result_down() -> None:
    case = build_case()
    candidate = CandidateLead(
        title="MISSING black tri fluffy corgi",
        source_name="public_web",
        source_url="https://example.com/repost",
        snippet="Please share this flyer.",
        location_text="Conroe TX",
        found_at=case.last_seen_at,
        tags=["female", "corgi"],
        image_similarity=0.2,
        repost_penalty=0.9,
    )

    result = score_candidate(case, candidate)
    assert result.final_score < 0.35
    assert any("penalty" in line.lower() for line in result.explanation)
