"""Tests for export bundle."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from lostdog_mcp.schemas import CandidateLead, MissingDogCase
from lostdog_mcp.services.case_service import case_create
from lostdog_mcp.services.candidate_service import score_and_upsert_lead
from lostdog_mcp.services.export_service import case_export_bundle


def test_export_bundle_creates_files(db_session, tmp_path):
    intake = MissingDogCase(
        title="Missing corgi",
        last_seen_at=datetime(2025, 6, 26, 18, 0, 0),
        last_seen_location="Conroe TX",
        breed_guess="corgi",
        sex="female",
    )
    case = case_create(db_session, intake)
    lead = CandidateLead(
        title="Found corgi",
        source_name="public_web",
        source_url="https://example.com/found",
        snippet="A corgi found in Conroe.",
        location_text="Conroe TX",
        tags=["corgi"],
    )
    score_and_upsert_lead(db_session, case.id, lead)

    result = case_export_bundle(db_session, case.id, output_dir=str(tmp_path))
    assert result["candidate_count"] == 1

    json_path = Path(result["json_path"])
    md_path = Path(result["md_path"])
    assert json_path.exists()
    assert md_path.exists()

    bundle = json.loads(json_path.read_text())
    assert bundle["case"]["title"] == "Missing corgi"
    assert len(bundle["candidates"]) == 1

    report = md_path.read_text()
    assert "Missing corgi" in report
