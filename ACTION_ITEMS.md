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

**2026-07-26 — bug-fix pass + interview-track reliability**
- Fixed 10 reported bugs: session-delete not persisting, typed/recorded-answer
  clobbering, spacebar-recording hang, refresh restarting the interview from
  scratch, TTS audio surviving navigation away from the interview, "Practice
  again"/Continue not resuming, missing End Session control on the Dashboard,
  a mute bug that silently dropped in-flight interviewer audio, no delete-all
  action, and unstyled problem/constraints text
- Added `GET /interview/{id}/resume` — sessions are now resumable by id
  instead of being start-only, closing the gap that caused several of the
  above
- Root-caused and fixed a real C++ code-execution bug (not just a
  boilerplate-rendering issue): the generated harness's `#include`/`using
  namespace std` came after the candidate's class in the merged source, so
  most C++ submissions using `vector`/`string`/`stack` failed to compile —
  this affected real candidate runs, not only the boilerplate step
  (`services/harness_generator.py::merge_cpp_sources`)
- Added a compile-check for generated boilerplate itself (previously only the
  reference solution was verified, so a boilerplate with an empty/non-
  compiling body could still be served to candidates)
- Added `docs/EVALUATION_METRICS.md` — a proposed framework for measuring
  interviewer context-accuracy, evaluation-score validity, and technical-track
  correctness

## Open items

Carried forward, not yet picked up:

- **Harness-generation reliability for Java/C++** — first-try verification
  pass rate for LLM-generated test harnesses is inconsistent (observed ~40-60%
  on a small sample); some failures are genuine LLM driver-code bugs (e.g.
  binding a temporary to a non-const C++ reference) rather than boilerplate
  issues. Needs prompt iteration or a retry-with-feedback loop.
- **Human-vs-bot evaluation-score correlation study** — no data yet on
  whether `overall_score` actually agrees with a human interviewer's rating
  (see `docs/EVALUATION_METRICS.md` §2). Needs 30+ real transcripts before it
  can start.
- **Azure monitoring/alerting** — no Application Insights, Log Analytics, or
  alert rules currently exist for the Container Apps deployment. Drafted in
  `infra/monitoring.bicep` + `infra/deploy-monitoring.sh` (Log Analytics
  workspace, Application Insights, 5xx/restart/high-CPU alerts on all three
  apps) but **not yet deployed** — needs `environmentId`/alert-email filled
  in, a `what-if` review, and the metric names double-checked against the
  live resource before applying (see comments in the script).
- **Seniority/role differentiation** — formally out of scope as of v4.0, but
  still the most-requested "make it feel less generic" ask if revisited.
