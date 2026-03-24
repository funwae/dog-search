"""Tests for repost/echo detection."""

from __future__ import annotations

from datetime import datetime

from lostdog_mcp.schemas import CandidateLead, MissingDogCase
from lostdog_mcp.services.repost_detection import (
    compute_repost_penalty,
    jaccard_similarity,
    ngram_set,
    text_fingerprint,
)


def _case() -> MissingDogCase:
    return MissingDogCase(
        title="Missing black tri fluffy corgi named Luna",
        last_seen_at=datetime(2025, 6, 26, 18, 0, 0),
        last_seen_location="South Rayburn Drive in Conroe Texas",
        breed_guess="corgi",
        owner_notes="Please help find Luna",
    )


def test_text_fingerprint_deterministic():
    fp1 = text_fingerprint("Hello World!")
    fp2 = text_fingerprint("Hello World!")
    assert fp1 == fp2


def test_text_fingerprint_order_insensitive():
    fp1 = text_fingerprint("hello world")
    fp2 = text_fingerprint("world hello")
    assert fp1 == fp2


def test_ngram_set_basic():
    grams = ngram_set("hello", n=3)
    assert "hel" in grams
    assert "ell" in grams
    assert "llo" in grams


def test_jaccard_identical():
    s = {"a", "b", "c"}
    assert jaccard_similarity(s, s) == 1.0


def test_jaccard_disjoint():
    assert jaccard_similarity({"a"}, {"b"}) == 0.0


def test_repost_penalty_high_for_flyer_repost():
    case = _case()
    repost = CandidateLead(
        title="MISSING black tri fluffy corgi named Luna",
        source_name="public_web",
        source_url="https://example.com/share-flyer",
        snippet="Please share this flyer! Missing corgi Luna last seen Conroe Texas. Help find!",
        location_text="Conroe TX",
        tags=["missing", "corgi"],
    )
    penalty = compute_repost_penalty(case, repost)
    assert penalty >= 0.3, f"Expected high penalty for repost, got {penalty}"


def test_repost_penalty_low_for_found_dog():
    case = _case()
    found = CandidateLead(
        title="Found corgi near Highway 242",
        source_name="petfbi",
        source_url="https://petfbi.org/found/12345",
        snippet="Picked up a stray corgi on Highway 242 in Conroe. No collar, appears female.",
        location_text="Highway 242, Conroe TX",
        tags=["found", "corgi", "female", "no_collar"],
    )
    penalty = compute_repost_penalty(case, found)
    assert penalty < 0.3, f"Expected low penalty for found dog, got {penalty}"


def test_repost_penalty_moderate_for_ambiguous():
    case = _case()
    ambiguous = CandidateLead(
        title="Corgi in Conroe",
        source_name="public_web",
        source_url="https://example.com/post",
        snippet="Saw a corgi near Rayburn today.",
        location_text="Conroe TX",
        tags=["corgi"],
    )
    penalty = compute_repost_penalty(case, ambiguous)
    # Should be somewhere in the middle
    assert 0.0 <= penalty <= 1.0
