"""Shelter / found-pet source adapter.

Phase 1: stub that returns mock data. Will be replaced with real API
integrations (PetFBI, PawBoost, Petco Love Lost) in Phase 2.
"""

from __future__ import annotations

from datetime import datetime

from ..schemas import CandidateLead

SUPPORTED_SOURCES = ["petfbi", "pawboost", "petcolovelost"]


async def search_shelters(
    breed: str | None,
    location: str,
    sex: str = "unknown",
    *,
    sources: list[str] | None = None,
    page: int = 1,
    limit: int = 10,
) -> list[CandidateLead]:
    """Query shelter/found-pet sources. Returns stubs for Phase 1."""
    selected = sources or SUPPORTED_SOURCES
    results: list[CandidateLead] = []
    for source in selected:
        if source not in SUPPORTED_SOURCES:
            continue
        results.extend(_stub_results(source, breed, location))
    return results[:limit]


def _stub_results(source: str, breed: str | None, location: str) -> list[CandidateLead]:
    breed_text = breed or "unknown breed"
    return [
        CandidateLead(
            title=f"[{source}] Found {breed_text} near {location}",
            source_name=source,
            source_url=f"https://{source}.example.com/listing/stub-001",
            snippet=f"Stub listing from {source} for a {breed_text} in {location}.",
            location_text=location,
            found_at=datetime.now(),
            tags=["found", "stub"],
        ),
    ]
