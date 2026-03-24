"""LostDog Deep Search MCP server — JSON-RPC 2.0 over stdio."""

from __future__ import annotations

import asyncio
import json
import sys
from typing import Any

from .config import Settings
from .storage.db import get_engine, get_session
from .storage.models import CaseRow, CandidateRow  # noqa: F401 — ensure tables created
from .schemas import MissingDogCase
from .services.case_service import case_create, case_get, case_list, case_to_schema
from .services.candidate_service import candidate_list, candidate_score, candidate_mark, score_and_upsert_lead
from .services.crawl_service import crawl_run, crawl_digest
from .services.export_service import case_export_bundle
from .services.evidence_service import archive_page, list_evidence
from .adapters.public_web import search_public_web
from .adapters.shelters import search_shelters
from .adapters.browser_session import search_with_session, BrowserSessionDisabledError

_settings: Settings | None = None


def _get_settings() -> Settings:
    global _settings
    if _settings is None:
        _settings = Settings.from_env()
    return _settings


# ── Tool registry ────────────────────────────────────────────────────────

TOOLS: dict[str, dict[str, Any]] = {
    "case_create": {
        "description": "Create a new missing-dog case.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "title": {"type": "string"},
                "last_seen_at": {"type": "string", "description": "ISO datetime"},
                "last_seen_location": {"type": "string"},
                "breed_guess": {"type": "string"},
                "sex": {"type": "string", "enum": ["female", "male", "unknown"]},
                "spayed_neutered": {"type": "boolean"},
                "chip_status": {"type": "string", "enum": ["chipped", "not_chipped", "unknown"]},
                "collar_status": {"type": "string", "enum": ["wearing", "not_wearing", "unknown"]},
                "medical_notes": {"type": "string"},
                "owner_notes": {"type": "string"},
                "image_paths": {"type": "array", "items": {"type": "string"}},
                "last_seen_lat": {"type": "number"},
                "last_seen_lng": {"type": "number"},
            },
            "required": ["title", "last_seen_at", "last_seen_location"],
        },
    },
    "case_get": {
        "description": "Get a case summary by ID.",
        "inputSchema": {
            "type": "object",
            "properties": {"case_id": {"type": "string"}},
            "required": ["case_id"],
        },
    },
    "search_public_web": {
        "description": "Search public web for found-dog listings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "radius_miles": {"type": "integer", "default": 25},
                "days_back": {"type": "integer", "default": 14},
                "page": {"type": "integer", "default": 1},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["case_id"],
        },
    },
    "search_found_pet_sources": {
        "description": "Search shelter/found-pet sources.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "sources": {"type": "array", "items": {"type": "string"}},
                "page": {"type": "integer", "default": 1},
                "limit": {"type": "integer", "default": 10},
            },
            "required": ["case_id"],
        },
    },
    "candidate_list": {
        "description": "List ranked candidate leads for a case.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "page": {"type": "integer", "default": 1},
                "limit": {"type": "integer", "default": 20},
            },
            "required": ["case_id"],
        },
    },
    "candidate_score": {
        "description": "Get explainable score breakdown for a candidate.",
        "inputSchema": {
            "type": "object",
            "properties": {"candidate_id": {"type": "string"}},
            "required": ["candidate_id"],
        },
    },
    "candidate_mark": {
        "description": "Mark a candidate with a review status.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "candidate_id": {"type": "string"},
                "status": {"type": "string", "enum": ["likely_match", "false_positive", "repost", "follow_up", "uncertain"]},
                "notes": {"type": "string"},
            },
            "required": ["candidate_id", "status"],
        },
    },
    "crawl_run": {
        "description": "Run a full crawl pass for a case.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "radius_miles": {"type": "integer", "default": 25},
                "days_back": {"type": "integer", "default": 14},
                "sources": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["case_id"],
        },
    },
    "case_export_bundle": {
        "description": "Export case report as markdown + JSON bundle.",
        "inputSchema": {
            "type": "object",
            "properties": {"case_id": {"type": "string"}},
            "required": ["case_id"],
        },
    },
    "case_add_images": {
        "description": "Add images to a case and generate perceptual hash embeddings.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "image_paths": {"type": "array", "items": {"type": "string"}},
            },
            "required": ["case_id", "image_paths"],
        },
    },
    "crawl_digest": {
        "description": "Get a summary of candidates since a given timestamp.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "since": {"type": "string", "description": "ISO datetime"},
            },
            "required": ["case_id"],
        },
    },
    "search_browser_session": {
        "description": "Search using the user's authenticated browser session (must be enabled).",
        "inputSchema": {
            "type": "object",
            "properties": {
                "case_id": {"type": "string"},
                "url": {"type": "string", "description": "URL to search"},
                "cookies": {"type": "object", "description": "Session cookies"},
            },
            "required": ["case_id", "url"],
        },
    },
    "evidence_archive": {
        "description": "Archive a web page as evidence.",
        "inputSchema": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
    "evidence_list": {
        "description": "List all archived evidence.",
        "inputSchema": {"type": "object", "properties": {}},
    },
    "case_list": {
        "description": "List all active cases.",
        "inputSchema": {"type": "object", "properties": {
            "status": {"type": "string", "default": "active"},
        }},
    },
}


# ── Tool handlers ────────────────────────────────────────────────────────

def _handle_case_create(args: dict) -> dict:
    settings = _get_settings()
    intake = MissingDogCase(
        title=args["title"],
        last_seen_at=args["last_seen_at"],
        last_seen_location=args["last_seen_location"],
        breed_guess=args.get("breed_guess"),
        sex=args.get("sex", "unknown"),
        spayed_neutered=args.get("spayed_neutered"),
        chip_status=args.get("chip_status", "unknown"),
        collar_status=args.get("collar_status", "unknown"),
        medical_notes=args.get("medical_notes"),
        owner_notes=args.get("owner_notes"),
        image_paths=args.get("image_paths", []),
    )
    with get_session(settings.db_url) as session:
        row = case_create(session, intake, lat=args.get("last_seen_lat"), lng=args.get("last_seen_lng"))
        return {"case_id": row.id, "title": row.title, "status": row.status}


def _handle_case_get(args: dict) -> dict:
    settings = _get_settings()
    with get_session(settings.db_url) as session:
        row = case_get(session, args["case_id"])
        if row is None:
            return {"error": "Case not found"}
        return {
            "id": row.id, "title": row.title, "last_seen_at": row.last_seen_at.isoformat(),
            "last_seen_location": row.last_seen_location, "breed_guess": row.breed_guess,
            "sex": row.sex, "status": row.status,
        }


def _handle_search_public_web(args: dict) -> dict:
    settings = _get_settings()
    with get_session(settings.db_url) as session:
        row = case_get(session, args["case_id"])
        if row is None:
            return {"error": "Case not found"}
        leads = asyncio.get_event_loop().run_until_complete(
            search_public_web(
                row.breed_guess, row.last_seen_location, row.sex,
                radius_miles=args.get("radius_miles", 25),
                days_back=args.get("days_back", 14),
                page=args.get("page", 1),
                limit=args.get("limit", 10),
            )
        )
        rows = []
        for lead in leads:
            c = score_and_upsert_lead(session, args["case_id"], lead)
            rows.append({"id": c.id, "title": c.title, "score": c.final_score})
        return {"candidates_added": len(rows), "candidates": rows}


def _handle_search_found_pet(args: dict) -> dict:
    settings = _get_settings()
    with get_session(settings.db_url) as session:
        row = case_get(session, args["case_id"])
        if row is None:
            return {"error": "Case not found"}
        leads = asyncio.get_event_loop().run_until_complete(
            search_shelters(
                row.breed_guess, row.last_seen_location, row.sex,
                sources=args.get("sources"),
                page=args.get("page", 1),
                limit=args.get("limit", 10),
            )
        )
        rows = []
        for lead in leads:
            c = score_and_upsert_lead(session, args["case_id"], lead)
            rows.append({"id": c.id, "title": c.title, "score": c.final_score})
        return {"candidates_added": len(rows), "candidates": rows}


def _handle_candidate_list(args: dict) -> dict:
    settings = _get_settings()
    with get_session(settings.db_url) as session:
        rows = candidate_list(session, args["case_id"], page=args.get("page", 1), limit=args.get("limit", 20))
        return {
            "case_id": args["case_id"],
            "count": len(rows),
            "candidates": [
                {"id": r.id, "title": r.title, "source": r.source_name, "score": r.final_score, "status": r.status}
                for r in rows
            ],
        }


def _handle_candidate_score(args: dict) -> dict:
    settings = _get_settings()
    with get_session(settings.db_url) as session:
        score = candidate_score(session, args["candidate_id"])
        if score is None:
            return {"error": "Candidate not found"}
        return score.model_dump()


def _handle_candidate_mark(args: dict) -> dict:
    settings = _get_settings()
    with get_session(settings.db_url) as session:
        row = candidate_mark(session, args["candidate_id"], args["status"], args.get("notes"))
        if row is None:
            return {"error": "Candidate not found"}
        return {"id": row.id, "status": row.status}


def _handle_crawl_run(args: dict) -> dict:
    settings = _get_settings()
    with get_session(settings.db_url) as session:
        rows = crawl_run(
            session, args["case_id"],
            radius_miles=args.get("radius_miles", 25),
            days_back=args.get("days_back", 14),
            sources=args.get("sources"),
        )
        return {
            "case_id": args["case_id"],
            "candidates_found": len(rows),
            "candidates": [{"id": r.id, "title": r.title, "score": r.final_score} for r in rows],
        }


def _handle_export(args: dict) -> dict:
    settings = _get_settings()
    with get_session(settings.db_url) as session:
        return case_export_bundle(session, args["case_id"], output_dir=settings.cases_dir)


def _handle_case_add_images(args: dict) -> dict:
    import json as _json
    from .vision.embedder import embed_image
    settings = _get_settings()
    with get_session(settings.db_url) as session:
        row = case_get(session, args["case_id"])
        if row is None:
            return {"error": "Case not found"}
        existing = _json.loads(row.image_paths_json)
        new_paths = args.get("image_paths", [])
        existing.extend(new_paths)
        row.image_paths_json = _json.dumps(existing)
        session.add(row)
        session.commit()
        embeddings_info = []
        for path in new_paths:
            try:
                embs = embed_image(path)
                embeddings_info.append({"path": path, "embeddings": len(embs), "labels": [e.label for e in embs]})
            except Exception as e:
                embeddings_info.append({"path": path, "error": str(e)})
        return {"case_id": args["case_id"], "total_images": len(existing), "new_embeddings": embeddings_info}


def _handle_crawl_digest(args: dict) -> dict:
    from datetime import datetime as _dt
    settings = _get_settings()
    since = None
    if args.get("since"):
        since = _dt.fromisoformat(args["since"])
    with get_session(settings.db_url) as session:
        return crawl_digest(session, args["case_id"], since=since)


def _handle_search_browser_session(args: dict) -> dict:
    settings = _get_settings()
    try:
        leads = asyncio.get_event_loop().run_until_complete(
            search_with_session(
                args["url"],
                cookies=args.get("cookies"),
                location="",
            )
        )
    except BrowserSessionDisabledError as e:
        return {"error": str(e)}
    if not leads:
        return {"candidates_added": 0, "candidates": []}
    with get_session(settings.db_url) as session:
        rows = []
        for lead in leads:
            c = score_and_upsert_lead(session, args["case_id"], lead)
            rows.append({"id": c.id, "title": c.title, "score": c.final_score})
        return {"candidates_added": len(rows), "candidates": rows}


def _handle_evidence_archive(args: dict) -> dict:
    settings = _get_settings()
    result = asyncio.get_event_loop().run_until_complete(
        archive_page(args["url"], evidence_dir=settings.evidence_dir)
    )
    return result


def _handle_evidence_list(args: dict) -> dict:
    settings = _get_settings()
    evidence = list_evidence(settings.evidence_dir)
    return {"count": len(evidence), "evidence": evidence[:50]}


def _handle_case_list(args: dict) -> dict:
    settings = _get_settings()
    with get_session(settings.db_url) as session:
        rows = case_list(session, status=args.get("status", "active"))
        return {
            "count": len(rows),
            "cases": [
                {"id": r.id, "title": r.title, "location": r.last_seen_location, "status": r.status}
                for r in rows
            ],
        }


_HANDLERS: dict[str, Any] = {
    "case_create": _handle_case_create,
    "case_get": _handle_case_get,
    "case_list": _handle_case_list,
    "case_add_images": _handle_case_add_images,
    "search_public_web": _handle_search_public_web,
    "search_found_pet_sources": _handle_search_found_pet,
    "search_browser_session": _handle_search_browser_session,
    "candidate_list": _handle_candidate_list,
    "candidate_score": _handle_candidate_score,
    "candidate_mark": _handle_candidate_mark,
    "crawl_run": _handle_crawl_run,
    "crawl_digest": _handle_crawl_digest,
    "case_export_bundle": _handle_export,
    "evidence_archive": _handle_evidence_archive,
    "evidence_list": _handle_evidence_list,
}


# ── JSON-RPC protocol ───────────────────────────────────────────────────

def _jsonrpc_response(id: Any, result: Any) -> dict:
    return {"jsonrpc": "2.0", "id": id, "result": result}


def _jsonrpc_error(id: Any, code: int, message: str) -> dict:
    return {"jsonrpc": "2.0", "id": id, "error": {"code": code, "message": message}}


def handle_request(request: dict) -> dict:
    req_id = request.get("id")
    method = request.get("method", "")
    params = request.get("params", {})

    if method == "initialize":
        return _jsonrpc_response(req_id, {
            "protocolVersion": "2024-11-05",
            "capabilities": {"tools": {"listChanged": False}},
            "serverInfo": {"name": "lostdog-deepsearch-mcp", "version": "0.2.0"},
        })

    if method == "notifications/initialized":
        return _jsonrpc_response(req_id, {})

    if method == "tools/list":
        tool_list = [{"name": name, "description": spec["description"], "inputSchema": spec["inputSchema"]} for name, spec in TOOLS.items()]
        return _jsonrpc_response(req_id, {"tools": tool_list})

    if method == "tools/call":
        tool_name = params.get("name", "")
        tool_args = params.get("arguments", {})
        handler = _HANDLERS.get(tool_name)
        if handler is None:
            return _jsonrpc_error(req_id, -32601, f"Unknown tool: {tool_name}")
        try:
            result = handler(tool_args)
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps(result, default=str)}],
            })
        except Exception as exc:
            return _jsonrpc_response(req_id, {
                "content": [{"type": "text", "text": json.dumps({"error": str(exc)})}],
                "isError": True,
            })

    return _jsonrpc_error(req_id, -32601, f"Method not found: {method}")


def main() -> None:
    """Run the MCP server over stdio (one JSON-RPC message per line)."""
    settings = Settings.from_env()
    # Ensure engine is initialised
    get_engine(settings.db_url)

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            resp = _jsonrpc_error(None, -32700, "Parse error")
            sys.stdout.write(json.dumps(resp) + "\n")
            sys.stdout.flush()
            continue

        resp = handle_request(request)
        sys.stdout.write(json.dumps(resp) + "\n")
        sys.stdout.flush()


if __name__ == "__main__":
    main()
