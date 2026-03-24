"""Petco Love Lost adapter — queries their public API.

Petco Love Lost (formerly Finding Rover) uses a facial-recognition based
pet matching service. They have a public-facing search API.
"""

from __future__ import annotations

from datetime import datetime

import httpx

from ..schemas import CandidateLead

API_URL = "https://lost.petcolove.org/api/v1/search"
BASE_URL = "https://lost.petcolove.org"
USER_AGENT = "LostDog-DeepSearch/0.2 (missing pet search tool)"


async def search_petcolovelost(
    breed: str | None,
    location: str,
    sex: str = "unknown",
    *,
    lat: float | None = None,
    lng: float | None = None,
    radius_miles: int = 25,
    page: int = 1,
    limit: int = 20,
) -> list[CandidateLead]:
    """Search Petco Love Lost for found dogs."""
    # Their API typically requires lat/lng
    if lat is None or lng is None:
        return []

    payload = {
        "species": "dog",
        "status": "found",
        "latitude": lat,
        "longitude": lng,
        "radius": radius_miles,
        "page": page,
        "per_page": limit,
    }
    if breed:
        payload["breed"] = breed
    if sex != "unknown":
        payload["sex"] = sex

    results: list[CandidateLead] = []
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.post(
                API_URL,
                json=payload,
                headers={
                    "User-Agent": USER_AGENT,
                    "Accept": "application/json",
                },
            )
            if resp.status_code == 200:
                data = resp.json()
                results = _parse_api_results(data, location)
    except (httpx.HTTPError, Exception):
        pass
    return results[:limit]


def _parse_api_results(data: dict, default_location: str) -> list[CandidateLead]:
    """Parse Petco Love Lost API JSON response."""
    results: list[CandidateLead] = []
    pets = data.get("pets", data.get("results", data.get("data", [])))
    if not isinstance(pets, list):
        return results

    for pet in pets:
        pet_id = pet.get("id", "")
        name = pet.get("name", pet.get("title", "Found Dog"))
        description = pet.get("description", pet.get("notes", ""))
        location_text = pet.get("city", pet.get("location", default_location))
        breed_text = pet.get("breed", pet.get("primary_breed", ""))
        sex_text = pet.get("sex", pet.get("gender", ""))
        found_date = pet.get("found_date", pet.get("date", None))
        lat = pet.get("latitude", pet.get("lat", None))
        lng = pet.get("longitude", pet.get("lng", None))

        found_at = None
        if found_date:
            try:
                found_at = datetime.fromisoformat(str(found_date))
            except (ValueError, TypeError):
                pass

        url = f"{BASE_URL}/pet/{pet_id}" if pet_id else f"{BASE_URL}/search"

        tags: list[str] = ["found"]
        if breed_text:
            tags.extend(breed_text.lower().split())
        if sex_text:
            tags.append(sex_text.lower())

        results.append(
            CandidateLead(
                title=f"Found: {name}" if name else "Found Dog",
                source_name="petcolovelost",
                source_url=url,
                snippet=description[:500] if description else f"{breed_text} found in {location_text}",
                location_text=str(location_text),
                found_at=found_at,
                lat=float(lat) if lat else None,
                lng=float(lng) if lng else None,
                tags=tags,
            )
        )

    return results
