"""Evidence storage service — archive web pages and track provenance."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import httpx

USER_AGENT = "LostDog-DeepSearch/0.2 (missing pet search tool)"


async def archive_page(url: str, evidence_dir: str = "./data/evidence") -> dict:
    """Download and archive a web page as evidence.

    Saves the raw HTML and metadata. Returns archive info.
    """
    out_dir = Path(evidence_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    url_hash = hashlib.sha256(url.encode()).hexdigest()[:16]
    timestamp = datetime.now(timezone.utc)
    ts_slug = timestamp.strftime("%Y%m%d_%H%M%S")
    filename = f"{ts_slug}_{url_hash}"

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            resp.raise_for_status()
            content = resp.text
    except (httpx.HTTPError, Exception) as e:
        return {"error": str(e), "url": url, "archived": False}

    html_path = out_dir / f"{filename}.html"
    html_path.write_text(content, encoding="utf-8")

    content_hash = hashlib.sha256(content.encode()).hexdigest()

    meta = {
        "url": url,
        "archived_at": timestamp.isoformat(),
        "content_hash": content_hash,
        "html_path": str(html_path),
        "status_code": resp.status_code,
        "content_length": len(content),
    }
    meta_path = out_dir / f"{filename}.meta.json"
    meta_path.write_text(json.dumps(meta, indent=2))

    return {**meta, "archived": True}


def check_duplicate_evidence(evidence_dir: str, content_hash: str) -> str | None:
    """Check if we already have evidence with this content hash.

    Returns the path to existing evidence, or None.
    """
    out_dir = Path(evidence_dir)
    if not out_dir.exists():
        return None
    for meta_file in out_dir.glob("*.meta.json"):
        try:
            meta = json.loads(meta_file.read_text())
            if meta.get("content_hash") == content_hash:
                return meta.get("html_path")
        except (json.JSONDecodeError, OSError):
            continue
    return None


def list_evidence(evidence_dir: str = "./data/evidence") -> list[dict]:
    """List all archived evidence files."""
    out_dir = Path(evidence_dir)
    if not out_dir.exists():
        return []
    evidence: list[dict] = []
    for meta_file in sorted(out_dir.glob("*.meta.json"), reverse=True):
        try:
            meta = json.loads(meta_file.read_text())
            evidence.append(meta)
        except (json.JSONDecodeError, OSError):
            continue
    return evidence
