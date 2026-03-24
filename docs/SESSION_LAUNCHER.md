# Claude Code Session Launcher

You are building `lostdog-deepsearch-mcp`, a local-first MCP server and operator workflow for finding a missing dog from flyer text, images, public web search, official shelter/found-pet sources, and explicitly user-authorized browser sessions.

Read these first, in order:
1. @CLAUDE.md
2. @README.md
3. @docs/PRODUCT_BRIEF.md
4. @docs/ARCHITECTURE.md
5. @docs/MCP_TOOLS.md
6. @docs/PHASE_PLAN.md
7. @docs/SAFETY_AND_POLICY.md

Execution mode:
- Work phase by phase.
- Do not skip tests.
- Keep outputs compact and reviewable.
- Prefer shipping a narrow working slice over broad mock structure.
- Stop after each milestone with:
  - what was built
  - what remains
  - exact commands to run
  - known risks

First task:
Build Phase 1 end-to-end:
- scaffold the package
- implement `case_create`, `case_get`, `search_public_web`, `candidate_list`, `candidate_score`, `case_export_bundle`
- wire sqlite persistence
- add one public-web adapter and one shelter/found-pet adapter stub
- add tests for ranking and case lifecycle
- make the server runnable with `python -m lostdog_mcp.server`

When uncertain:
- choose the simplest local-first implementation that preserves the architecture.
