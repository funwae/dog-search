"""Shelter / found-pet source adapter — aggregates real adapters.

Dispatches searches to PetFBI, PawBoost, and Petco Love Lost adapters,
collecting results in parallel.
"""

from __future__ import annotations

import asyncio
import logging

from ..schemas import CandidateLead
from .pawboost import search_pawboost
from .petcolovelost import search_petcolovelost
from .petfbi import search_petfbi

logger = logging.getLogger(__name__)

SUPPORTED_SOURCES = ["petfbi", "pawboost", "petcolovelost"]


async def search_shelters(
    breed: str | None,
    location: str,
    sex: str = "unknown",
    *,
    sources: list[str] | None = None,
    lat: float | None = None,
    lng: float | None = None,
    page: int = 1,
    limit: int = 10,
) -> list[CandidateLead]:
    """Query shelter/found-pet sources in parallel."""
    selected = sources or SUPPORTED_SOURCES
    tasks = []

    for source in selected:
        if source == "petfbi":
            tasks.append(search_petfbi(breed, location, sex, page=page, limit=limit))
        elif source == "pawboost":
            tasks.append(search_pawboost(breed, location, sex, page=page, limit=limit))
        elif source == "petcolovelost":
            tasks.append(search_petcolovelost(breed, location, sex, lat=lat, lng=lng, page=page, limit=limit))
        else:
            logger.warning(f"Unknown source: {source}")

    if not tasks:
        return []

    all_results = await asyncio.gather(*tasks, return_exceptions=True)
    results: list[CandidateLead] = []
    for result in all_results:
        if isinstance(result, list):
            results.extend(result)
        elif isinstance(result, Exception):
            logger.warning(f"Adapter error: {result}")
    return results[:limit]
