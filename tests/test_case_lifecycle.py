"""Tests for case create/get/list lifecycle."""

from __future__ import annotations

from datetime import datetime

from lostdog_mcp.schemas import MissingDogCase
from lostdog_mcp.services.case_service import case_create, case_get, case_list, case_to_schema


def _intake() -> MissingDogCase:
    return MissingDogCase(
        title="Missing black tri fluffy corgi",
        last_seen_at=datetime(2025, 6, 26, 18, 0, 0),
        last_seen_location="South Rayburn Drive in Conroe Texas",
        breed_guess="corgi",
        sex="female",
        chip_status="chipped",
        collar_status="not_wearing",
    )


def test_case_create_and_get(db_session):
    intake = _intake()
    row = case_create(db_session, intake, lat=30.314, lng=-95.455)
    assert row.id is not None
    assert row.title == "Missing black tri fluffy corgi"
    assert row.last_seen_lat == 30.314

    fetched = case_get(db_session, row.id)
    assert fetched is not None
    assert fetched.id == row.id


def test_case_list_returns_active_only(db_session):
    intake = _intake()
    row1 = case_create(db_session, intake)
    row2 = case_create(db_session, intake)

    # Mark one as closed
    row2.status = "closed"
    db_session.add(row2)
    db_session.commit()

    active = case_list(db_session, status="active")
    assert len(active) == 1
    assert active[0].id == row1.id


def test_case_to_schema_roundtrip(db_session):
    intake = _intake()
    row = case_create(db_session, intake)
    schema = case_to_schema(row)
    assert schema.title == intake.title
    assert schema.breed_guess == intake.breed_guess
    assert schema.sex == "female"


def test_case_get_nonexistent(db_session):
    assert case_get(db_session, "nonexistent") is None
