"""Crawl orchestration: run all adapters for a case."""

from __future__ import annotations

import asyncio

from sqlmodel import Session

from ..adapters.public_web import search_public_web
from ..adapters.shelters import search_shelters
from ..schemas import CandidateLead
from ..services.candidate_service import score_and_upsert_lead
from ..services.case_service import case_get
from ..storage.models import CandidateRow


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

    leads = asyncio.get_event_loop().run_until_complete(
        _gather_leads(
            breed=case_row.breed_guess,
            location=case_row.last_seen_location,
            sex=case_row.sex,
            radius_miles=radius_miles,
            days_back=days_back,
            sources=sources,
        )
    )

    rows: list[CandidateRow] = []
    for lead in leads:
        row = score_and_upsert_lead(session, case_id, lead)
        rows.append(row)
    return rows


async def _gather_leads(
    breed: str | None,
    location: str,
    sex: str,
    radius_miles: int,
    days_back: int,
    sources: list[str] | None,
) -> list[CandidateLead]:
    web_task = search_public_web(breed, location, sex, radius_miles=radius_miles, days_back=days_back)
    shelter_task = search_shelters(breed, location, sex, sources=sources)
    web_results, shelter_results = await asyncio.gather(web_task, shelter_task)
    return web_results + shelter_results
