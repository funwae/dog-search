"""PawBoost adapter — scrapes public found-pet listings.

PawBoost (pawboost.com) is a widely-used lost/found pet service.
Their found-pet listings are publicly accessible.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from ..schemas import CandidateLead

BASE_URL = "https://www.pawboost.com"
USER_AGENT = "LostDog-DeepSearch/0.2 (missing pet search tool)"


async def search_pawboost(
    breed: str | None,
    location: str,
    sex: str = "unknown",
    *,
    page: int = 1,
    limit: int = 20,
) -> list[CandidateLead]:
    """Search PawBoost for found dogs near a location."""
    # PawBoost uses location-based URL paths
    location_slug = quote_plus(location.lower().replace(",", "").replace(" ", "-"))
    search_url = f"{BASE_URL}/lost-found-pets/{location_slug}"

    results: list[CandidateLead] = []
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(
                search_url,
                params={"type": "found", "animal": "dog", "page": page},
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            results = _parse_results(resp.text, location)
    except (httpx.HTTPError, Exception):
        pass
    return results[:limit]


def _parse_results(html: str, default_location: str) -> list[CandidateLead]:
    """Parse PawBoost search results page."""
    soup = BeautifulSoup(html, "lxml")
    results: list[CandidateLead] = []

    for card in soup.select(".pet-card, .alert-card, .lost-found-card, .card, article"):
        title_el = card.select_one("h2, h3, h4, .pet-name, .card-title")
        link_el = card.select_one("a[href]")
        desc_el = card.select_one("p, .description, .card-text")
        location_el = card.select_one(".location, .city, address, .pet-location")
        date_el = card.select_one(".date, time, .posted-date")

        title = title_el.get_text(strip=True) if title_el else "Found Dog"
        url = ""
        if link_el and link_el.get("href"):
            href = link_el["href"]
            url = href if href.startswith("http") else f"{BASE_URL}{href}"
        snippet = desc_el.get_text(strip=True) if desc_el else ""
        loc_text = location_el.get_text(strip=True) if location_el else default_location

        found_at = None
        if date_el:
            try:
                date_text = date_el.get("datetime", date_el.get_text(strip=True))
                found_at = datetime.fromisoformat(date_text)
            except (ValueError, TypeError):
                pass

        if url:
            results.append(
                CandidateLead(
                    title=title,
                    source_name="pawboost",
                    source_url=url,
                    snippet=snippet[:500],
                    location_text=loc_text,
                    found_at=found_at,
                    tags=_extract_tags(title + " " + snippet),
                )
            )

    return results


def _extract_tags(text: str) -> list[str]:
    text_lower = text.lower()
    tags: list[str] = ["found"]
    breed_keywords = [
        "lab", "labrador", "pit", "pitbull", "shepherd", "husky", "beagle",
        "corgi", "poodle", "chihuahua", "terrier", "bulldog", "boxer",
        "retriever", "dachshund", "collie", "rottweiler", "schnauzer",
    ]
    for breed in breed_keywords:
        if breed in text_lower:
            tags.append(breed)
    if "female" in text_lower:
        tags.append("female")
    if "male" in text_lower and "female" not in text_lower:
        tags.append("male")
    if "no collar" in text_lower:
        tags.append("no_collar")
    elif "collar" in text_lower:
        tags.append("collar")
    if "chip" in text_lower or "microchip" in text_lower:
        tags.append("chip")
    return tags
