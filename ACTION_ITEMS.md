# Action Items

Living tracker for open work across the project. Update this file (or link out
to it) whenever an item is picked up, finished, or dropped — keep it in sync
with actual PR/issue state rather than letting it drift.

For day-to-day task assignment and status, use a proper tracker instead of
editing this file constantly — **GitHub Projects** (free, built into this repo,
no new tool to onboard people onto) is the recommended default. This file
stays as the durable, versioned summary of *what* the items are and *why*.

Sourced from a full audit of every version of the design doc in
`design-doc-history/` (9 versions, 2026-06-17 through today) cross-checked
against current code — not just recent PR activity — so this reflects the
project's full lifecycle, not a snapshot of the last few days.

## Project Timeline

What actually shipped, version by version, per the design doc's own
"Built"/"Scope" tables at each point in time:

**v1.0 POC — 2026-06-17**
- Behavioral track and Technical track built
- LangChain LCEL agent (not plain API calls) for the interviewer
- Pydantic-validated evaluation output (schema-enforced, not free text)
- Groq primary LLM with Ollama Cloud fallback
- Supabase auth + session history
- Piston code execution flagged as unreliable (the public API was rate-limited)
- Still planned at this point: System Design track, question bank, seniority/role selectors, evaluation benchmarking

**v2.0 — 2026-06-24**
- Deployed to Azure Container Apps (Sweden Central), full CI/CD via GitHub Actions
- Self-hosted Piston + Wandbox fallback — fixed the v1.0 reliability problem
- Dynamic test runner: the LLM generates test *data* only, not code; a harness template we control actually runs it
- Four-layer guardrail added to stop the AI leaking interview answers
- System Design track (Excalidraw canvas) built

**v3.0 ("industry-grade" rewrite) — 2026-06-30**
- Question bank grew to 210 verified LeetCode problems, each verified by running a reference solution through the sandbox before import
- Dynamic interviewer (`question_generator.py`) — decides per session whether to reuse a bank question or generate a new one
- Automated test suite and structured logging identified as gaps (not yet built at this point)

**2026-07-01 (2 revisions)**
- Question bank grew again: 210 LeetCode + 77 CodeContests (DeepMind) + 8 hand-written = 295 technical questions, all test-verified before import

**v4.0 — 2026-07-08 (`e52a88f`)**
- Question bank reached its current 357 total (295 technical + 42 behavioral + 20 system-design)
- Postgres-backed sliding-window rate limiter shipped
- Session concurrency cap (max 3 active sessions) + idle timeout shipped
- Async code-execution job queue shipped
- System-design diagram scoring shipped
- Structured logging + pytest/Vitest CI suite shipped
- JD upload for personalized question selection shipped (`Dashboard.jsx`)
- This version also recorded specific reviewer feedback on concurrency, scalability, and rate-limiting that was never resolved

**v4.0 (current) — 2026-07-08 (`92b5fa3`)**
- Consolidated into today's `DESIGN.md`
- Seniority/role differentiation and human-rater benchmarking formally reclassified as out of scope instead of being left as stale "planned" items

**Since then**
- Boilerplate/reset-button fix
- Evaluation self-critique pass
- Usage analytics
- CI path-filtering + mypy/tsc gates
- Real deploy automation
- Design-doc history archive
