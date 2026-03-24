"""Repost / duplicate detection using text fingerprinting.

Detects when a candidate is a repost of the original flyer (an "echo")
rather than an independent sighting or find report.
"""

from __future__ import annotations

import hashlib
import re
from collections import Counter

from ..schemas import CandidateLead, MissingDogCase


def text_fingerprint(text: str) -> str:
    """Create a normalized fingerprint of text for dedup."""
    # Normalize: lowercase, strip punctuation, collapse whitespace
    text = text.lower()
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    # Sort words to be order-insensitive for short texts
    words = sorted(text.split())
    return hashlib.md5(" ".join(words).encode()).hexdigest()[:12]


def ngram_set(text: str, n: int = 3) -> set[str]:
    """Generate character n-grams from normalized text."""
    text = re.sub(r"[^\w\s]", "", text.lower()).strip()
    text = re.sub(r"\s+", " ", text)
    if len(text) < n:
        return {text}
    return {text[i : i + n] for i in range(len(text) - n + 1)}


def jaccard_similarity(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def compute_repost_penalty(case: MissingDogCase, candidate: CandidateLead) -> float:
    """Compute how likely a candidate is a repost of the original flyer.

    Returns a penalty score from 0.0 (not a repost) to 1.0 (definitely a repost).

    Signals:
    - High text overlap with the original case description
    - Contains phrases like "missing", "lost", "help find", "please share"
    - Lacks "found" or "spotted" language
    - Title closely matches the original flyer title
    """
    signals: list[float] = []

    # 1. Title similarity (strong signal)
    title_sim = jaccard_similarity(
        ngram_set(case.title),
        ngram_set(candidate.title),
    )
    signals.append(min(1.0, title_sim * 1.5))

    # 2. Text overlap with case description
    case_text = " ".join(filter(None, [
        case.title, case.last_seen_location,
        case.breed_guess, case.owner_notes,
    ]))
    candidate_text = " ".join([candidate.title, candidate.snippet, candidate.location_text])
    text_sim = jaccard_similarity(ngram_set(case_text), ngram_set(candidate_text))
    signals.append(text_sim)

    # 3. Repost language detection
    repost_phrases = [
        "missing", "lost", "help find", "please share", "share this",
        "have you seen", "reward", "bring home", "call if seen",
        "still missing", "update", "day missing",
    ]
    found_phrases = [
        "found", "spotted", "seen at", "picked up", "turned in",
        "at shelter", "stray", "wandering", "rescued",
    ]

    ctext_lower = candidate_text.lower()
    repost_count = sum(1 for p in repost_phrases if p in ctext_lower)
    found_count = sum(1 for p in found_phrases if p in ctext_lower)

    if repost_count > 0 and found_count == 0:
        signals.append(min(1.0, repost_count * 0.25))
    elif found_count > 0:
        signals.append(0.0)
    else:
        signals.append(0.1)

    # 4. Source-based heuristic (social media shares are more likely reposts)
    if candidate.source_name == "public_web":
        # Web results with "missing" in title are likely reposts
        if any(w in candidate.title.lower() for w in ["missing", "lost"]):
            signals.append(0.5)
        else:
            signals.append(0.0)
    else:
        signals.append(0.0)

    # Weighted average
    weights = [0.35, 0.30, 0.25, 0.10]
    penalty = sum(s * w for s, w in zip(signals, weights))
    return min(1.0, max(0.0, penalty))
