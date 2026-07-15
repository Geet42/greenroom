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

| Version | Date | What shipped since the last version |
|---|---|---|
| v1.0 POC | 2026-06-17 | Behavioral + Technical tracks, LangChain LCEL agent, Pydantic-validated evaluation, Groq→Ollama Cloud fallback, Supabase auth/session history. Piston code execution flagged as unreliable (public API rate-limited). System Design track, question bank, seniority/role selectors, and benchmarking all still planned. |
| v2.0 | 2026-06-24 | Deployed to Azure Container Apps (Sweden Central) with full CI/CD via GitHub Actions. Self-hosted Piston + Wandbox fallback (fixed the v1.0 reliability problem). Dynamic test runner (LLM generates test *data*, not code — a harness template we control runs it). Four-layer guardrail against answer leaks. System Design track (Excalidraw canvas) built. |
| v3.0 ("industry-grade" rewrite) | 2026-06-30 | Question bank grew to 210 verified LeetCode problems (sandboxed dual-solution verification before import). Dynamic interviewer (`question_generator.py`) — decides bank vs. generated question per session. Automated test suite and structured logging identified as new gaps (not yet built). |
| 2026-07-01 (2 revisions) | 2026-07-01 | Question bank grew again: 210 LeetCode + 77 CodeContests (DeepMind) + 8 hand-written = 295 technical questions, all test-verified pre-import. |
| v4.0 | 2026-07-08 (`e52a88f`) | Question bank reached its current 357 (295 technical + 42 behavioral + 20 system-design). Postgres-backed sliding-window rate limiter, session concurrency cap (max 3) + idle timeout, async code-execution job queue, system-design diagram scoring, structured logging, pytest+Vitest CI suite — all landed. JD upload for personalized question selection shipped (`Dashboard.jsx`). This version also recorded specific reviewer feedback on concurrency/scalability/rate-limiting that was never resolved — see **Performance and Scalability** below. |
| v4.0 (current) | 2026-07-08 (`92b5fa3`) | Consolidated into today's `DESIGN.md`. Seniority/role differentiation and human-rater benchmarking formally reclassified as **Non-Goals** rather than left as stale "planned" items (see below). |
| Since | 2026-07-08 → today | Boilerplate/reset-button fix, evaluation self-critique pass, usage analytics, CI path-filtering + mypy/tsc gates, real deploy automation, design-doc history archive — tracked in the sections below. |
