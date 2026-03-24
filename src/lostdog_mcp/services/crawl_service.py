"""Crawl orchestration: run all adapters for a case, apply repost detection."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from sqlmodel import Session, select

from ..adapters.public_web import search_public_web
from ..adapters.shelters import search_shelters
from ..schemas import CandidateLead
from ..services.candidate_service import score_and_upsert_lead
from ..services.case_service import case_get, case_to_schema
from ..services.repost_detection import compute_repost_penalty
from ..storage.models import CandidateRow, CaseRow

logger = logging.getLogger(__name__)


def crawl_run(
    session: Session,
    case_id: str,
    *,
    radius_miles: int = 25,
    days_back: int = 14,
    sources: list[str] | None = None,
) -> list[CandidateRow]:
    case_row = case_get(session, case_id)
    if case_row is None:
        raise ValueError(f"Case {case_id} not found")

    case_schema = case_to_schema(case_row)

    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as pool:
                leads = pool.submit(
                    lambda: asyncio.run(_gather_leads(
                        breed=case_row.breed_guess,
                        location=case_row.last_seen_location,
                        sex=case_row.sex,
                        lat=case_row.last_seen_lat,
                        lng=case_row.last_seen_lng,
                        radius_miles=radius_miles,
                        days_back=days_back,
                        sources=sources,
                    ))
                ).result()
        else:
            leads = loop.run_until_complete(
                _gather_leads(
                    breed=case_row.breed_guess,
                    location=case_row.last_seen_location,
                    sex=case_row.sex,
                    lat=case_row.last_seen_lat,
                    lng=case_row.last_seen_lng,
                    radius_miles=radius_miles,
                    days_back=days_back,
                    sources=sources,
                )
            )
    except RuntimeError:
        leads = asyncio.run(
            _gather_leads(
                breed=case_row.breed_guess,
                location=case_row.last_seen_location,
                sex=case_row.sex,
                lat=case_row.last_seen_lat,
                lng=case_row.last_seen_lng,
                radius_miles=radius_miles,
                days_back=days_back,
                sources=sources,
            )
        )

    # Apply repost detection before scoring
    for lead in leads:
        penalty = compute_repost_penalty(case_schema, lead)
        lead.repost_penalty = penalty

    rows: list[CandidateRow] = []
    for lead in leads:
        row = score_and_upsert_lead(session, case_id, lead)
        rows.append(row)

    # Update case timestamp
    case_row.updated_at = datetime.now(timezone.utc)
    session.add(case_row)
    session.commit()

    return rows


def crawl_digest(
    session: Session,
    case_id: str,
    since: datetime | None = None,
) -> dict:
    """Return summary of new/changed candidates since a timestamp."""
    case_row = case_get(session, case_id)
    if case_row is None:
        raise ValueError(f"Case {case_id} not found")

    stmt = select(CandidateRow).where(CandidateRow.case_id == case_id)
    if since:
        stmt = stmt.where(CandidateRow.created_at >= since)
    stmt = stmt.order_by(CandidateRow.final_score.desc())  # type: ignore[union-attr]

    candidates = list(session.exec(stmt).all())
    high_score = [c for c in candidates if c.final_score >= 0.5]
    medium_score = [c for c in candidates if 0.25 <= c.final_score < 0.5]
    low_score = [c for c in candidates if c.final_score < 0.25]

    return {
        "case_id": case_id,
        "since": since.isoformat() if since else "all",
        "total_candidates": len(candidates),
        "high_confidence": len(high_score),
        "medium_confidence": len(medium_score),
        "low_confidence": len(low_score),
        "top_leads": [
            {"id": c.id, "title": c.title, "score": c.final_score, "source": c.source_name}
            for c in high_score[:5]
        ],
    }


async def _gather_leads(
    breed: str | None,
    location: str,
    sex: str,
    lat: float | None,
    lng: float | None,
    radius_miles: int,
    days_back: int,
    sources: list[str] | None,
) -> list[CandidateLead]:
    web_task = search_public_web(breed, location, sex, radius_miles=radius_miles, days_back=days_back)
    shelter_task = search_shelters(breed, location, sex, sources=sources, lat=lat, lng=lng)
    results = await asyncio.gather(web_task, shelter_task, return_exceptions=True)

    leads: list[CandidateLead] = []
    for result in results:
        if isinstance(result, list):
            leads.extend(result)
        elif isinstance(result, Exception):
            logger.warning(f"Adapter error during crawl: {result}")
    return leads
