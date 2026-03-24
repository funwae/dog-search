"""Candidate management: upsert, list, score, mark."""

from __future__ import annotations

import hashlib
import json

from sqlmodel import Session, select

from ..ranking import score_candidate
from ..schemas import CandidateLead, ScoreBreakdown
from ..services.case_service import case_get, case_to_schema
from ..storage.models import CandidateRow


def _content_hash(lead: CandidateLead) -> str:
    blob = f"{lead.source_url}|{lead.title}|{lead.snippet}".encode()
    return hashlib.sha256(blob).hexdigest()[:16]


def candidate_upsert(session: Session, case_id: str, lead: CandidateLead, score: ScoreBreakdown) -> CandidateRow:
    chash = _content_hash(lead)
    stmt = select(CandidateRow).where(CandidateRow.case_id == case_id, CandidateRow.content_hash == chash)
    existing = session.exec(stmt).first()
    if existing is not None:
        existing.final_score = score.final_score
        existing.explanation_json = json.dumps(score.explanation)
        session.add(existing)
        session.commit()
        session.refresh(existing)
        return existing

    row = CandidateRow(
        case_id=case_id,
        title=lead.title,
        source_name=lead.source_name,
        source_url=str(lead.source_url),
        snippet=lead.snippet,
        location_text=lead.location_text,
        found_at=lead.found_at,
        lat=lead.lat,
        lng=lead.lng,
        tags_json=json.dumps(lead.tags),
        image_similarity=lead.image_similarity,
        text_similarity=lead.text_similarity,
        attribute_similarity=lead.attribute_similarity,
        repost_penalty=lead.repost_penalty,
        final_score=score.final_score,
        explanation_json=json.dumps(score.explanation),
        content_hash=chash,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def candidate_list(session: Session, case_id: str, *, page: int = 1, limit: int = 20) -> list[CandidateRow]:
    offset = (page - 1) * limit
    stmt = (
        select(CandidateRow)
        .where(CandidateRow.case_id == case_id)
        .order_by(CandidateRow.final_score.desc())  # type: ignore[union-attr]
        .offset(offset)
        .limit(limit)
    )
    return list(session.exec(stmt).all())


def candidate_score(session: Session, candidate_id: str) -> ScoreBreakdown | None:
    row = session.get(CandidateRow, candidate_id)
    if row is None:
        return None
    return ScoreBreakdown(
        text_score=row.text_similarity,
        geo_score=0.0,
        time_score=0.0,
        attribute_score=row.attribute_similarity,
        image_score=row.image_similarity,
        repost_penalty=row.repost_penalty,
        final_score=row.final_score,
        explanation=json.loads(row.explanation_json),
    )


def candidate_mark(session: Session, candidate_id: str, status: str, notes: str | None = None) -> CandidateRow | None:
    row = session.get(CandidateRow, candidate_id)
    if row is None:
        return None
    row.status = status
    if notes is not None:
        row.operator_notes = notes
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def score_and_upsert_lead(session: Session, case_id: str, lead: CandidateLead) -> CandidateRow:
    case_row = case_get(session, case_id)
    if case_row is None:
        raise ValueError(f"Case {case_id} not found")
    case_schema = case_to_schema(case_row)
    score = score_candidate(
        case_schema,
        lead,
        last_seen_lat=case_row.last_seen_lat,
        last_seen_lng=case_row.last_seen_lng,
    )
    return candidate_upsert(session, case_id, lead, score)
