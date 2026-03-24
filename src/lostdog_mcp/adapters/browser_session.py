"""Browser-session adapter — use user's authenticated session.

This adapter is DISABLED by default and requires explicit opt-in via
LOSTDOG_ENABLE_BROWSER_SESSION=true environment variable.

It searches user-authorized sources (e.g., Nextdoor, Facebook groups)
using cookies from the user's browser. The user must explicitly provide
their session cookies — we never steal or intercept them.
"""

from __future__ import annotations

import os
from datetime import datetime

import httpx
from bs4 import BeautifulSoup

from ..schemas import CandidateLead

USER_AGENT = "Mozilla/5.0 (compatible; LostDog-DeepSearch/0.2)"


class BrowserSessionDisabledError(Exception):
    """Raised when browser session mode is not enabled."""


def _check_enabled() -> None:
    enabled = os.getenv("LOSTDOG_ENABLE_BROWSER_SESSION", "false").lower() in {"1", "true", "yes", "on"}
    if not enabled:
        raise BrowserSessionDisabledError(
            "Browser session mode is disabled. Set LOSTDOG_ENABLE_BROWSER_SESSION=true to enable."
        )


async def search_with_session(
    url: str,
    cookies: dict[str, str] | None = None,
    *,
    location: str = "",
) -> list[CandidateLead]:
    """Fetch a URL using optional session cookies and extract found-pet leads.

    The user must explicitly provide cookies and enable this mode.
    """
    _check_enabled()

    if not cookies:
        cookies = {}

    results: list[CandidateLead] = []
    try:
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True, cookies=cookies) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            results = _extract_leads(resp.text, url, location)
    except BrowserSessionDisabledError:
        raise
    except (httpx.HTTPError, Exception):
        pass
    return results


def _extract_leads(html: str, source_url: str, default_location: str) -> list[CandidateLead]:
    """Generic lead extraction from an arbitrary page."""
    soup = BeautifulSoup(html, "lxml")
    results: list[CandidateLead] = []

    # Look for posts/cards/articles containing dog-related content
    dog_keywords = {"dog", "puppy", "pup", "canine", "found", "stray", "lost"}

    for container in soup.select("article, .post, .card, .feed-item, [data-testid]"):
        text = container.get_text(" ", strip=True)
        text_lower = text.lower()

        # Only process if it mentions dogs
        if not any(kw in text_lower for kw in dog_keywords):
            continue

        # Skip if it's clearly not a found-dog post
        if "found" not in text_lower and "stray" not in text_lower and "spotted" not in text_lower:
            continue

        link = container.select_one("a[href]")
        url = ""
        if link and link.get("href"):
            href = link["href"]
            url = href if href.startswith("http") else source_url

        title = text[:100].split("\n")[0] if text else "Found Dog"

        results.append(
            CandidateLead(
                title=title,
                source_name="browser_session",
                source_url=url or source_url,
                snippet=text[:500],
                location_text=default_location,
                tags=["found", "browser_session"],
            )
        )

    return results
