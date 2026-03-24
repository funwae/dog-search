"""Geocoding service using OpenStreetMap Nominatim (free, no API key).

Rate limit: 1 request per second per Nominatim usage policy.
Results are cached in-memory to avoid repeated lookups.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import httpx

NOMINATIM_URL = "https://nominatim.openstreetmap.org/search"
USER_AGENT = "LostDog-DeepSearch/0.2 (missing pet search tool; contact: github)"

_cache: dict[str, "GeoResult | None"] = {}
_last_request_time: float = 0.0


@dataclass(frozen=True)
class GeoResult:
    lat: float
    lng: float
    display_name: str


async def geocode(location: str) -> GeoResult | None:
    """Convert a location string to lat/lng coordinates.

    Uses Nominatim with a 1-second rate limit between requests.
    Returns None if location cannot be resolved.
    """
    global _last_request_time

    key = location.strip().lower()
    if key in _cache:
        return _cache[key]

    # Respect rate limit
    elapsed = time.time() - _last_request_time
    if elapsed < 1.1:
        time.sleep(1.1 - elapsed)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                NOMINATIM_URL,
                params={
                    "q": location,
                    "format": "json",
                    "limit": 1,
                    "countrycodes": "us",
                },
                headers={"User-Agent": USER_AGENT},
            )
            _last_request_time = time.time()
            resp.raise_for_status()
            data = resp.json()

            if data and isinstance(data, list) and len(data) > 0:
                result = GeoResult(
                    lat=float(data[0]["lat"]),
                    lng=float(data[0]["lon"]),
                    display_name=data[0].get("display_name", location),
                )
                _cache[key] = result
                return result
    except (httpx.HTTPError, KeyError, ValueError, IndexError):
        pass

    _cache[key] = None
    return None


def geocode_sync(location: str) -> GeoResult | None:
    """Synchronous geocoding wrapper."""
    import asyncio
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(lambda: asyncio.run(geocode(location))).result()
        return loop.run_until_complete(geocode(location))
    except RuntimeError:
        return asyncio.run(geocode(location))
