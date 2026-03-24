# LostDog Deep Search MCP — Project Instructions

See @README.md for setup and @docs/PRODUCT_BRIEF.md for goals.
See @docs/ARCHITECTURE.md for subsystem boundaries.
See @docs/MCP_TOOLS.md for MCP tool contracts.

## Mission
Build a local-first MCP server and operator console that helps find a missing dog by:
1. ingesting flyer text and images,
2. searching public and user-authorized sources,
3. ranking likely matches using text + geospatial + image similarity,
4. preserving evidence and operator review history.

## Hard constraints
- Do not implement access-control bypasses.
- Do not scrape private/community-only sources unless the user explicitly enables use of their own authenticated browser session.
- Prefer public pages, official shelter sources, found-pet databases, and user-supplied exports.
- Never auto-contact strangers, shelters, or site operators.
- Never auto-post to social media.
- Every candidate must preserve source URL, timestamp, screenshot path if captured, and extraction method.
- Every confidence score must be explainable by component scores.

## Coding rules
- Python 3.12.
- Typed code only.
- Pydantic for schemas.
- SQLModel or SQLAlchemy for storage.
- Keep adapters thin and pure; business logic belongs in services/.
- Keep tool outputs compact and paginated.
- Add tests for every ranking rule change.
- Prefer deterministic scoring over opaque heuristics where possible.

## MCP rules
- Expose only stable, operator-safe tools.
- All tools must validate input with strict schemas.
- Long outputs must support page/limit and summary-only modes.
- Expose resources for active cases, candidate lists, and daily reports.
- Make tools composable: intake → crawl → match → review → export.

## Search rules
- Geofence-first.
- Time-window-first.
- Deduplicate reposts aggressively.
- Penalize reposts of the original flyer so the system does not surface “echoes” as leads.
- Favor leads with new images, exact local roads, shelter intake IDs, or found-date overlap.

## Vision rules
- Use dog detection/cropping before embedding.
- Store multiple embeddings per image: whole image, dog crop, head crop if possible.
- Keep image matching advisory, not authoritative.
- Treat coat pattern, ear silhouette, blaze/mask, chest white distribution, and side profile as separate signals.

## Review UX rules
- Show why a candidate scored high.
- Make false-positive marking one action.
- Support “same flyer repost”, “not enough evidence”, “likely same dog”, and “needs human follow-up”.
