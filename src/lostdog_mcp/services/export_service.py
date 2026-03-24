"""Export a case bundle: markdown summary + JSON data."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path

from sqlmodel import Session

from ..services.candidate_service import candidate_list
from ..services.case_service import case_get


def case_export_bundle(
    session: Session,
    case_id: str,
    output_dir: str = "./data/cases",
) -> dict:
    case_row = case_get(session, case_id)
    if case_row is None:
        raise ValueError(f"Case {case_id} not found")

    candidates = candidate_list(session, case_id, limit=100)
    out = Path(output_dir) / case_id
    out.mkdir(parents=True, exist_ok=True)

    # JSON export
    case_dict = {
        "id": case_row.id,
        "title": case_row.title,
        "last_seen_at": case_row.last_seen_at.isoformat(),
        "last_seen_location": case_row.last_seen_location,
        "breed_guess": case_row.breed_guess,
        "sex": case_row.sex,
        "status": case_row.status,
    }
    candidates_list = []
    for c in candidates:
        candidates_list.append({
            "id": c.id,
            "title": c.title,
            "source_name": c.source_name,
            "source_url": c.source_url,
            "snippet": c.snippet,
            "final_score": c.final_score,
            "status": c.status,
            "explanation": json.loads(c.explanation_json),
        })

    bundle = {"case": case_dict, "candidates": candidates_list, "exported_at": datetime.now(timezone.utc).isoformat()}
    json_path = out / "bundle.json"
    json_path.write_text(json.dumps(bundle, indent=2))

    # Markdown export
    md_lines = [
        f"# Case: {case_row.title}",
        f"**ID:** {case_row.id}",
        f"**Last seen:** {case_row.last_seen_location} at {case_row.last_seen_at}",
        f"**Breed:** {case_row.breed_guess or 'unknown'}",
        f"**Sex:** {case_row.sex}",
        "",
        f"## Candidates ({len(candidates_list)})",
        "",
    ]
    for i, c in enumerate(candidates_list, 1):
        md_lines.append(f"### {i}. {c['title']} (score: {c['final_score']:.3f})")
        md_lines.append(f"- Source: {c['source_name']} — {c['source_url']}")
        md_lines.append(f"- Status: {c['status']}")
        md_lines.append(f"- {c['snippet'][:200]}")
        md_lines.append("")

    md_path = out / "report.md"
    md_path.write_text("\n".join(md_lines))

    return {
        "case_id": case_id,
        "json_path": str(json_path),
        "md_path": str(md_path),
        "candidate_count": len(candidates_list),
    }
