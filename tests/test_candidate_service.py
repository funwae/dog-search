"""Tests for candidate upsert, list, score, mark."""

from __future__ import annotations

from datetime import datetime, timedelta

from lostdog_mcp.schemas import CandidateLead, MissingDogCase
from lostdog_mcp.services.case_service import case_create
from lostdog_mcp.services.candidate_service import (
    candidate_list,
    candidate_mark,
    candidate_score,
    score_and_upsert_lead,
)


def _create_case(session):
    intake = MissingDogCase(
        title="Missing corgi",
        last_seen_at=datetime(2025, 6, 26, 18, 0, 0),
        last_seen_location="Conroe TX",
        breed_guess="corgi",
        sex="female",
        chip_status="chipped",
        collar_status="not_wearing",
    )
    return case_create(session, intake, lat=30.314, lng=-95.455)


def _make_lead(title: str = "Found corgi", score: float = 0.8) -> CandidateLead:
    return CandidateLead(
        title=title,
        source_name="public_web",
        source_url=f"https://example.com/{title.replace(' ', '-')}",
        snippet="A corgi was found near Conroe.",
        location_text="Conroe TX",
        found_at=datetime(2025, 6, 27, 8, 0, 0),
        lat=30.315,
        lng=-95.454,
        tags=["female", "corgi", "chip", "no_collar"],
        image_similarity=score,
    )


def test_score_and_upsert_creates_candidate(db_session):
    case = _create_case(db_session)
    lead = _make_lead()
    row = score_and_upsert_lead(db_session, case.id, lead)
    assert row.id is not None
    assert row.case_id == case.id
    assert row.final_score > 0


def test_duplicate_lead_updates_not_duplicates(db_session):
    case = _create_case(db_session)
    lead = _make_lead()
    row1 = score_and_upsert_lead(db_session, case.id, lead)
    row2 = score_and_upsert_lead(db_session, case.id, lead)
    assert row1.id == row2.id  # same row, not a duplicate

    all_candidates = candidate_list(db_session, case.id)
    assert len(all_candidates) == 1


def test_candidate_list_ordered_by_score(db_session):
    case = _create_case(db_session)
    score_and_upsert_lead(db_session, case.id, _make_lead("Low scorer", 0.1))
    score_and_upsert_lead(db_session, case.id, _make_lead("High scorer", 0.9))

    results = candidate_list(db_session, case.id)
    assert len(results) == 2
    assert results[0].final_score >= results[1].final_score


def test_candidate_score_breakdown(db_session):
    case = _create_case(db_session)
    row = score_and_upsert_lead(db_session, case.id, _make_lead())
    breakdown = candidate_score(db_session, row.id)
    assert breakdown is not None
    assert breakdown.final_score == row.final_score


def test_candidate_mark(db_session):
    case = _create_case(db_session)
    row = score_and_upsert_lead(db_session, case.id, _make_lead())
    marked = candidate_mark(db_session, row.id, "false_positive", "Not the right dog")
    assert marked is not None
    assert marked.status == "false_positive"
    assert marked.operator_notes == "Not the right dog"


def test_candidate_mark_nonexistent(db_session):
    assert candidate_mark(db_session, "nonexistent", "likely_match") is None
