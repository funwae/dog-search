"""Tests for crawl digest."""

from __future__ import annotations

from datetime import datetime, timedelta

from lostdog_mcp.schemas import CandidateLead, MissingDogCase
from lostdog_mcp.services.case_service import case_create
from lostdog_mcp.services.candidate_service import score_and_upsert_lead
from lostdog_mcp.services.crawl_service import crawl_digest


def _create_case_with_candidates(session, n=5):
    intake = MissingDogCase(
        title="Missing corgi",
        last_seen_at=datetime(2025, 6, 26, 18, 0, 0),
        last_seen_location="Conroe TX",
        breed_guess="corgi",
        sex="female",
    )
    case = case_create(session, intake, lat=30.314, lng=-95.455)

    for i in range(n):
        lead = CandidateLead(
            title=f"Found dog #{i}",
            source_name="public_web",
            source_url=f"https://example.com/dog-{i}",
            snippet=f"Dog found near Conroe #{i}",
            location_text="Conroe TX",
            found_at=datetime(2025, 6, 27, 8 + i, 0, 0),
            lat=30.315,
            lng=-95.454,
            tags=["found", "corgi", "female"] if i < 3 else ["found"],
            image_similarity=0.8 - (i * 0.15),
        )
        score_and_upsert_lead(session, case.id, lead)

    return case


def test_crawl_digest_all(db_session):
    case = _create_case_with_candidates(db_session)
    result = crawl_digest(db_session, case.id)
    assert result["total_candidates"] == 5
    assert result["case_id"] == case.id


def test_crawl_digest_has_confidence_tiers(db_session):
    case = _create_case_with_candidates(db_session)
    result = crawl_digest(db_session, case.id)
    total = result["high_confidence"] + result["medium_confidence"] + result["low_confidence"]
    assert total == result["total_candidates"]


def test_crawl_digest_since_filter(db_session):
    case = _create_case_with_candidates(db_session)
    # Filter from the future — should return 0
    future = datetime(2030, 1, 1)
    result = crawl_digest(db_session, case.id, since=future)
    assert result["total_candidates"] == 0
