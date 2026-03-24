from __future__ import annotations

from collections.abc import Iterable
from datetime import datetime
from math import acos, cos, radians, sin

from .schemas import CandidateLead, MissingDogCase, ScoreBreakdown


def normalize_text_tokens(value: str) -> set[str]:
    cleaned = "".join(ch.lower() if ch.isalnum() else " " for ch in value)
    return {token for token in cleaned.split() if len(token) >= 3}


def overlap_score(a: Iterable[str], b: Iterable[str]) -> float:
    set_a = set(a)
    set_b = set(b)
    if not set_a or not set_b:
        return 0.0
    return len(set_a & set_b) / len(set_a | set_b)


def geo_score(
    last_seen_lat: float | None,
    last_seen_lng: float | None,
    candidate_lat: float | None,
    candidate_lng: float | None,
    radius_miles: float = 25.0,
) -> float:
    if None in {last_seen_lat, last_seen_lng, candidate_lat, candidate_lng}:
        return 0.0
    distance = haversine_miles(last_seen_lat, last_seen_lng, candidate_lat, candidate_lng)
    if distance >= radius_miles:
        return 0.0
    return max(0.0, 1.0 - (distance / radius_miles))


def haversine_miles(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    earth_radius_miles = 3958.8
    lat1_r = radians(lat1)
    lat2_r = radians(lat2)
    lon1_r = radians(lon1)
    lon2_r = radians(lon2)
    return earth_radius_miles * acos(
        max(
            -1.0,
            min(
                1.0,
                sin(lat1_r) * sin(lat2_r)
                + cos(lat1_r) * cos(lat2_r) * cos(lon2_r - lon1_r),
            ),
        )
    )


def time_score(last_seen_at: datetime, found_at: datetime | None, decay_days: float = 14.0) -> float:
    if found_at is None:
        return 0.0
    delta_days = abs((found_at - last_seen_at).total_seconds()) / 86400.0
    if delta_days >= decay_days:
        return 0.0
    return max(0.0, 1.0 - (delta_days / decay_days))


def attribute_score(case: MissingDogCase, candidate: CandidateLead) -> float:
    attributes: list[float] = []
    tags = {tag.lower() for tag in candidate.tags}

    if case.breed_guess:
        breed_tokens = normalize_text_tokens(case.breed_guess)
        attributes.append(1.0 if breed_tokens & tags else 0.0)

    if case.sex != "unknown":
        attributes.append(1.0 if case.sex in tags else 0.0)

    if case.chip_status == "chipped":
        attributes.append(1.0 if "chip" in tags or "microchip" in tags else 0.0)

    if case.collar_status == "not_wearing":
        attributes.append(1.0 if "no_collar" in tags else 0.0)

    if not attributes:
        return 0.0
    return sum(attributes) / len(attributes)


def score_candidate(
    case: MissingDogCase,
    candidate: CandidateLead,
    *,
    last_seen_lat: float | None = None,
    last_seen_lng: float | None = None,
    radius_miles: float = 25.0,
) -> ScoreBreakdown:
    case_text = normalize_text_tokens(
        " ".join(
            piece
            for piece in [case.title, case.last_seen_location, case.breed_guess or "", case.owner_notes or ""]
            if piece
        )
    )
    candidate_text = normalize_text_tokens(
        " ".join([candidate.title, candidate.snippet, candidate.location_text, " ".join(candidate.tags)])
    )

    text_component = overlap_score(case_text, candidate_text)
    geo_component = geo_score(
        last_seen_lat,
        last_seen_lng,
        candidate.lat,
        candidate.lng,
        radius_miles=radius_miles,
    )
    time_component = time_score(case.last_seen_at, candidate.found_at)
    attribute_component = attribute_score(case, candidate)
    image_component = max(0.0, min(1.0, candidate.image_similarity))
    repost_penalty = max(0.0, min(1.0, candidate.repost_penalty))

    final_score = (
        0.28 * text_component
        + 0.24 * geo_component
        + 0.16 * time_component
        + 0.14 * attribute_component
        + 0.18 * image_component
        - 0.20 * repost_penalty
    )
    final_score = max(0.0, min(1.0, final_score))

    explanation: list[str] = []
    if text_component >= 0.2:
        explanation.append("Strong text overlap with case facts.")
    if geo_component >= 0.5:
        explanation.append("Candidate is geographically close to the last-seen area.")
    if time_component >= 0.5:
        explanation.append("Found date is close to the missing date.")
    if attribute_component >= 0.5:
        explanation.append("Candidate metadata agrees with breed/sex/collar/chip details.")
    if image_component >= 0.6:
        explanation.append("Image similarity is meaningfully above weak-match range.")
    if repost_penalty >= 0.5:
        explanation.append("Likely repost or duplicate of the original flyer; penalty applied.")
    if not explanation:
        explanation.append("No strong signals yet; keep as a low-confidence lead.")

    return ScoreBreakdown(
        text_score=round(text_component, 4),
        geo_score=round(geo_component, 4),
        time_score=round(time_component, 4),
        attribute_score=round(attribute_component, 4),
        image_score=round(image_component, 4),
        repost_penalty=round(repost_penalty, 4),
        final_score=round(final_score, 4),
        explanation=explanation,
    )
