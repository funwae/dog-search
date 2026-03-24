"""Case lifecycle: create, get, list."""

from __future__ import annotations

import json
from datetime import datetime, timezone

from sqlmodel import Session, select

from ..schemas import MissingDogCase
from ..storage.models import CaseRow


def case_create(session: Session, intake: MissingDogCase, *, lat: float | None = None, lng: float | None = None) -> CaseRow:
    row = CaseRow(
        title=intake.title,
        last_seen_at=intake.last_seen_at,
        last_seen_location=intake.last_seen_location,
        last_seen_lat=lat,
        last_seen_lng=lng,
        species=intake.species,
        breed_guess=intake.breed_guess,
        sex=intake.sex,
        spayed_neutered=intake.spayed_neutered,
        chip_status=intake.chip_status,
        collar_status=intake.collar_status,
        medical_notes=intake.medical_notes,
        owner_notes=intake.owner_notes,
        image_paths_json=json.dumps(intake.image_paths),
        status="active",
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def case_get(session: Session, case_id: str) -> CaseRow | None:
    return session.get(CaseRow, case_id)


def case_list(session: Session, status: str = "active") -> list[CaseRow]:
    stmt = select(CaseRow).where(CaseRow.status == status)
    return list(session.exec(stmt).all())


def case_to_schema(row: CaseRow) -> MissingDogCase:
    return MissingDogCase(
        title=row.title,
        last_seen_at=row.last_seen_at,
        last_seen_location=row.last_seen_location,
        breed_guess=row.breed_guess,
        sex=row.sex,
        spayed_neutered=row.spayed_neutered,
        chip_status=row.chip_status,
        collar_status=row.collar_status,
        medical_notes=row.medical_notes,
        owner_notes=row.owner_notes,
        image_paths=json.loads(row.image_paths_json),
    )
