# LostDog Deep Search MCP

Local-first starter repo for a missing-dog search system that Claude Code can immediately pick up and continue building.

## What is already here
- project instructions for Claude Code (`CLAUDE.md`)
- project MCP config (`.mcp.json`)
- full product and architecture docs (`docs/`)
- skill scaffold (`.claude/skills/`)
- Python package scaffold under `src/lostdog_mcp/`
- working ranking logic with tests
- launch scripts for Claude Code

## Quick start
```bash
python -m venv .venv && source .venv/bin/activate && pip install -e .[dev] && pytest
```

## One-line Claude Code start
From the repo root:

```bash
claude "Read @docs/SESSION_LAUNCHER.md, follow it exactly, and build Phase 1 now."
```

Or use the helper script:

```bash
./scripts/open-in-claude.sh
```

## Local placeholder server
This starter repo includes a minimal placeholder entrypoint so the package runs cleanly:

```bash
python -m lostdog_mcp.server
```

## Suggested first commit after upload
```bash
git init && git add . && git commit -m "Initial LostDog Deep Search MCP starter"
```
