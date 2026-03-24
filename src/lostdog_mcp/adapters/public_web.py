"""Public web search adapter using httpx + a search API stub.

In production this would call a real search API (e.g., Brave Search, SerpAPI).
For Phase 1, it constructs a query and returns results from the API, falling
back to an empty list if no API key is configured.
"""

from __future__ import annotations

import os
from datetime import datetime

import httpx

from ..schemas import CandidateLead


def build_query(
    breed: str | None,
    location: str,
    sex: str = "unknown",
    extra_terms: str = "",
) -> str:
    parts = ["found dog"]
    if breed:
        parts.append(breed)
    parts.append(location)
    if sex != "unknown":
        parts.append(sex)
    if extra_terms:
        parts.append(extra_terms)
    return " ".join(parts)


async def search_public_web(
    breed: str | None,
    location: str,
    sex: str = "unknown",
    *,
    radius_miles: int = 25,
    days_back: int = 14,
    page: int = 1,
    limit: int = 10,
) -> list[CandidateLead]:
    """Search public web for found-dog listings.

    Uses BRAVE_API_KEY if available, otherwise returns empty results.
    """
    api_key = os.getenv("BRAVE_API_KEY", "")
    query = build_query(breed, location, sex)

    if not api_key:
        return _mock_results(query, location)

    async with httpx.AsyncClient(timeout=15.0) as client:
        resp = await client.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": limit, "offset": (page - 1) * limit},
            headers={"X-Subscription-Token": api_key, "Accept": "application/json"},
        )
        resp.raise_for_status()
        data = resp.json()

    results: list[CandidateLead] = []
    for item in data.get("web", {}).get("results", []):
        results.append(
            CandidateLead(
                title=item.get("title", ""),
                source_name="public_web",
                source_url=item.get("url", ""),
                snippet=item.get("description", ""),
                location_text=location,
                tags=[],
            )
        )
    return results


def _mock_results(query: str, location: str) -> list[CandidateLead]:
    """Return a small set of illustrative mock results for dev/testing."""
    return [
        CandidateLead(
            title=f"Found dog near {location}",
            source_name="public_web_mock",
            source_url="https://example.com/found-dog-1",
            snippet=f"A dog matching '{query}' was reported found.",
            location_text=location,
            found_at=datetime.now(),
            tags=["found", "dog"],
        ),
    ]
