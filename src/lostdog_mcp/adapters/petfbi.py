"""PetFBI.org adapter — scrapes public found-dog listings.

PetFBI is a free lost/found pet database. Their search is publicly
accessible at https://petfbi.org/found/. We query their search
results page and parse the listing cards.
"""

from __future__ import annotations

from datetime import datetime
from urllib.parse import quote_plus

import httpx
from bs4 import BeautifulSoup

from ..schemas import CandidateLead

BASE_URL = "https://petfbi.org"
SEARCH_URL = f"{BASE_URL}/search/"
USER_AGENT = "LostDog-DeepSearch/0.2 (missing pet search tool)"


async def search_petfbi(
    breed: str | None,
    location: str,
    sex: str = "unknown",
    *,
    species: str = "dog",
    page: int = 1,
    limit: int = 20,
) -> list[CandidateLead]:
    """Search PetFBI for found dogs near a location."""
    params = {
        "animal": "Dog",
        "status": "Found",
        "location": location,
        "distance": "50",
    }
    if breed:
        params["breed"] = breed

    results: list[CandidateLead] = []
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(
                SEARCH_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            results = _parse_search_results(resp.text, location)
    except (httpx.HTTPError, Exception):
        # Return empty on network failures — adapter must not crash the crawl
        pass
    return results[:limit]


def _parse_search_results(html: str, default_location: str) -> list[CandidateLead]:
    """Parse PetFBI search result page HTML."""
    soup = BeautifulSoup(html, "lxml")
    results: list[CandidateLead] = []

    # PetFBI uses card-style listing divs
    for card in soup.select(".card, .listing-card, .pet-card, article"):
        title_el = card.select_one("h2, h3, h4, .card-title, .title")
        link_el = card.select_one("a[href]")
        desc_el = card.select_one("p, .description, .card-text, .snippet")
        location_el = card.select_one(".location, .city, .area, address")
        date_el = card.select_one(".date, time, .found-date")

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
                    source_name="petfbi",
                    source_url=url,
                    snippet=snippet[:500],
                    location_text=loc_text,
                    found_at=found_at,
                    tags=_extract_tags(title + " " + snippet),
                )
            )

    return results


def _extract_tags(text: str) -> list[str]:
    """Extract breed/attribute tags from text."""
    text_lower = text.lower()
    tags: list[str] = ["found"]
    breed_keywords = [
        "lab", "labrador", "pit", "pitbull", "shepherd", "husky", "beagle",
        "corgi", "poodle", "chihuahua", "terrier", "bulldog", "boxer",
        "retriever", "dachshund", "collie", "rottweiler", "schnauzer",
        "maltese", "shih tzu", "yorkie", "pomeranian", "dalmatian",
        "doberman", "mastiff", "malinois", "aussie", "australian",
        "great dane", "bernese", "havanese", "papillon", "weimaraner",
    ]
    for breed in breed_keywords:
        if breed in text_lower:
            tags.append(breed)
    if "female" in text_lower:
        tags.append("female")
    if "male" in text_lower and "female" not in text_lower:
        tags.append("male")
    if "collar" in text_lower:
        tags.append("collar" if "no collar" not in text_lower else "no_collar")
    if "chip" in text_lower or "microchip" in text_lower:
        tags.append("chip")
    return tags
