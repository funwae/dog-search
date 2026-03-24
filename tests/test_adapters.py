"""Tests for adapter parsing logic (offline, no network calls)."""

from __future__ import annotations

from lostdog_mcp.adapters.petfbi import _parse_search_results, _extract_tags
from lostdog_mcp.adapters.pawboost import _parse_results as pawboost_parse
from lostdog_mcp.adapters.petcolovelost import _parse_api_results
from lostdog_mcp.adapters.public_web import build_query


# ── Public web ───────────────────────────────────────────────────────────

def test_build_query_basic():
    q = build_query("corgi", "Conroe TX")
    assert "found dog" in q
    assert "corgi" in q
    assert "Conroe TX" in q


def test_build_query_with_sex():
    q = build_query("lab", "Austin TX", sex="female")
    assert "female" in q


def test_build_query_no_breed():
    q = build_query(None, "Dallas TX")
    assert "found dog" in q
    assert "Dallas TX" in q


# ── PetFBI ───────────────────────────────────────────────────────────────

def test_petfbi_parse_empty():
    results = _parse_search_results("<html><body></body></html>", "Conroe TX")
    assert results == []


def test_petfbi_parse_with_cards():
    html = """
    <html><body>
    <article>
        <h3>Found Female Lab Mix</h3>
        <a href="/pet/12345">View</a>
        <p>Found wandering near Highway 105.</p>
        <span class="location">Conroe, TX</span>
    </article>
    <article>
        <h3>Found Male Shepherd</h3>
        <a href="/pet/12346">View</a>
        <p>Stray shepherd picked up on FM 1488.</p>
    </article>
    </body></html>
    """
    results = _parse_search_results(html, "Conroe TX")
    assert len(results) == 2
    assert results[0].title == "Found Female Lab Mix"
    assert results[0].source_name == "petfbi"
    assert "petfbi.org" in results[0].source_url
    assert "lab" in results[0].tags


def test_petfbi_extract_tags():
    tags = _extract_tags("Found female golden retriever with collar")
    assert "female" in tags
    assert "retriever" in tags
    assert "found" in tags
    assert "collar" in tags


def test_petfbi_extract_tags_no_collar():
    tags = _extract_tags("Found dog no collar")
    assert "no_collar" in tags


# ── PawBoost ─────────────────────────────────────────────────────────────

def test_pawboost_parse_empty():
    results = pawboost_parse("<html><body></body></html>", "Austin TX")
    assert results == []


def test_pawboost_parse_with_cards():
    html = """
    <html><body>
    <div class="pet-card">
        <h3 class="pet-name">Found Beagle</h3>
        <a href="/alert/99999">View Alert</a>
        <p class="description">Found beagle near downtown, no collar, male.</p>
        <span class="location">Austin, TX</span>
    </div>
    </body></html>
    """
    results = pawboost_parse(html, "Austin TX")
    assert len(results) == 1
    assert results[0].source_name == "pawboost"
    assert "beagle" in results[0].tags


# ── Petco Love Lost ─────────────────────────────────────────────────────

def test_petcolovelost_parse_empty():
    results = _parse_api_results({}, "Houston TX")
    assert results == []


def test_petcolovelost_parse_results():
    data = {
        "pets": [
            {
                "id": "abc123",
                "name": "Unknown",
                "description": "Found a small brown dog",
                "city": "Houston, TX",
                "breed": "chihuahua mix",
                "sex": "female",
                "found_date": "2025-06-27",
                "latitude": 29.76,
                "longitude": -95.36,
            }
        ]
    }
    results = _parse_api_results(data, "Houston TX")
    assert len(results) == 1
    assert results[0].source_name == "petcolovelost"
    assert results[0].lat == 29.76
    assert "chihuahua" in results[0].tags
    assert "female" in results[0].tags


def test_petcolovelost_parse_alternative_keys():
    data = {
        "results": [
            {
                "id": "xyz",
                "title": "Stray Dog",
                "notes": "Found roaming in park",
                "location": "Dallas, TX",
                "primary_breed": "mixed",
                "gender": "male",
            }
        ]
    }
    results = _parse_api_results(data, "Dallas TX")
    assert len(results) == 1
    assert "male" in results[0].tags
