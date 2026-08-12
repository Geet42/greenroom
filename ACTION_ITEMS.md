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

**2026-07-27 to 2026-07-29 — question bank quality push + telemetry + a critical data gap found and fixed**

- Fixed a corrective-retry gap: Java/C++ harness generation now feeds the
  exact compiler/runtime error from a failed attempt back into the next
  retry instead of blindly re-guessing (`_GENERATION_ATTEMPTS` 3 -> 4)
- Fixed a caching bug where failed harness/signature generations were never
  remembered — every backfill run and every live candidate request
  re-attempted the full multi-try generation from scratch, indefinitely, for
  questions already proven to fail (`_UNSUPPORTED_MARKER` sentinel added)
- Fixed Node/JS boilerplate being structurally unreachable for ~200 of 218
  questions — a restrictive check meant it was never actually attempted, not
  failing
- Merged upstream telemetry dashboard work (`Telemetry.jsx`,
  `GET /analytics/stats`) — session completion rates, per-track average
  scores, 14-day activity, language usage, score distribution
- Fixed candidate-requested question switching on the technical track — a
  candidate can now ask for a different problem in plain language mid-session
  (previously stuck refused, since the guardrail couldn't tell "LLM went off
  script" apart from "candidate explicitly asked")
- Found and fixed 77 CodeContests-imported questions missing worked examples
  entirely (masked by a bug in an earlier one-off verification script)
- **Sourced real, official LeetCode starter code from a public dataset**
  (`neenza/leetcode-problems`, ~2,900 problems) and matched it to 193/218
  technical questions by title — eliminated LLM generation (and its ~40-60%
  first-try success rate) for the vast majority of Java/C++/Python/JS
  boilerplate; every match still compile-verified in the sandbox before caching
- For the ~140 questions where LLM-generated Java/C++ harnesses had
  permanently failed, **replaced them with verified equivalent problems**
  from the same dataset — each replacement's reference solution is
  sandbox-executed against the problem's own official example
  input/output before its harness is even built, and the old question is
  only deleted after the new one is fully built, compiled, and inserted.
  Net effect: java confirmed-unsupported dropped from ~105 to 28 questions,
  cpp from ~112 to 31, zero data loss, zero duplicate ids/titles
- **Found and fixed a critical, previously-undiscovered production gap**:
  Supabase's `questions` table only ever had the 295 technical rows —
  `question_bank.py`'s Supabase-vs-local-JSON fallback only activates when
  the whole table is *empty*, so the 42 behavioral + 20 system-design
  questions sitting in the local seed file were **never actually served to
  candidates**, since the table wasn't empty, just incomplete. This explains
  why zero system-design sessions had ever been completed. Added the missing
  `expected_elements`/`expected_components` migration (documented in
  `DESIGN.md`'s schema for months but never actually applied) and seeded all
  62 missing rows — all three tracks are now genuinely live for the first
  time
- Cleaned up scratch/temporary files that had leaked into the working tree
  (a 20MB local copy of the boilerplate dataset, throwaway JSON working
  files) and tightened `.gitignore` to prevent recurrence

**2026-07-29 to 2026-08-04 — code-execution backend migration, test coverage push, evaluation-quality fixes**

- **Replaced both code-execution backends with Judge0** (`eeb197b`): Wandbox's
  container runtime was confirmed dead in production (persistent OCI `crun:
  clone: Resource temporarily unavailable` error on every request), and
  emkc.org's public Piston API — the interim replacement for the self-hosted
  instance — went whitelist-only and stopped accepting new callers. New chain:
  Judge0 public instance → Judge0 via RapidAPI (optional key) → local
  in-container subprocess (Python/Node/C++; no fallback for Java) →
  unavailable. The self-hosted Piston Azure Container App is decommissioned;
  its config still sits unused in the repo (`piston/` directory) — see Open
  Items.
- **Added ad-hoc Java/C++ test support** (`services/adhoc_harness.py`) —
  previously only curated-bank questions got Java/C++ test execution; a
  problem the interviewer invented live in conversation had zero support and
  surfaced "not yet supported" regardless of language.
- **Fixed 3 specific harness-generation failures** (PR #39): broken
  quote-escaping crashing a printed JSON line, an int-range overflow, and a
  markdown-fence parsing bug — diagnosed against real Groq generations that
  had failed all 4 retry attempts.
- **Weighted question difficulty by inferred candidate seniority** (PR #45,
  `infer_seniority()`) — previously difficulty selection ignored the
  candidate's stated role entirely.
- **Fixed the submitted-code transcript bug** (PR #44) — `persist_message`
  was saving only the candidate's prose, silently dropping their code from
  the Supabase-persisted transcript the Results page renders.
- **Renamed nav labels** (PRs #41, #42) — interview-list page is now "Your
  Interviews" (was "Dashboard"), stats page is now "Dashboard" (was
  "Telemetry"); routes unchanged.
- **Rate-limited and payload-bound the analytics endpoints** (PR #29) — the
  only endpoints in the app without `check_rate_limit`, with an unbounded
  `properties` dict unlike every other request body.
- **Added missing foreign keys** (PR #30) — `analytics_events.session_id`
  and `rate_limit_events.user_id` were orphaned on session delete, unlike
  every other user/session-owned table.
- **Added `GET /api/interview/sessions`** (PR #36) — paginated, backend-owned
  session listing; `Dashboard.jsx` no longer queries Supabase directly (was
  the only place in the app bypassing the API layer for reads).
- **Cached TTS audio** (PR #35) — `edge-tts` was regenerating from scratch on
  every call, even for text already synthesized moments earlier; now cached
  on disk keyed by `sha256(voice:text)` with LRU eviction.
- **First-ever frontend hook test suite** (PR #38, 22 tests) and **first
  direct router-level tests for `interview.py`** (PR #34) — previously only
  the router's dependencies (`session_guard`, `persistence`, `rate_limit`)
  had coverage in isolation, and no frontend hook had any test at all. Plus
  dedicated unit suites for `session_guard.py` (PR #31, 15 tests) and
  `persistence.py` (PR #32, 12 tests), both previously untested despite being
  directly security/data-integrity relevant.
- **Found and fixed a critical, previously-undiscovered data bug**: 137 of
  210 class-based technical questions had `tests[].call` strings missing the
  `Solution().` prefix their own `function_name` implied — every Python/JS
  submission, including perfectly correct code, failed 100% of tests
  regardless of correctness. Corroborated by production telemetry (technical
  track averaging 2.4/10 vs. 5.0 behavioral / 4.0 system-design, 8 of 14
  completed sessions scoring 0-2). All 137 rows patched live; a related,
  independent JS-only bug (missing `new` keyword for class instantiation,
  affecting the same 137 questions) fixed in `test_runner.py`. Both verified
  live against Judge0.
- **Found and fixed a system-design diagram-scoring gap**: `evaluate_diagram`
  only read diagram descriptions embedded in a prior chat message, never the
  autosaved board state (`POST /api/interview/diagram`) — a candidate who
  drew their diagram and clicked "End session" without one more message got
  scored 0 ("no diagram submitted") even though their diagram was saved and
  rendered correctly on the Results page. Now reads the autosaved state
  directly; verified live end-to-end.
- **Fixed a push-to-talk / Monaco-editor conflict**: pressing Space to type
  code could trigger the push-to-talk mic instead, because Monaco's actual
  focused element doesn't always match the exact-tag check the handler used.
  Fixed by also checking ancestry against `.monaco-editor`.
- **Redundancy cleanup**: removed the unused `groq` dependency (only
  `langchain-groq` is imported), fixed an ESLint misconfiguration that was
  producing false-positive unused-import warnings across ~13 frontend files
  (missing `eslint-plugin-react` / `jsx-uses-vars`), consolidated
  `harness_generator.py`'s duplicate `_persist`/`_persist_signature` helpers
  into one, and moved an orphaned migration file into `supabase/migrations/`.

- **Moved the end-of-session evaluation report to Azure OpenAI (gpt-5-mini)**
  (`365b9d8`) — `evaluate_session`, `_self_critique`, and `evaluate_diagram`
  now run on Azure OpenAI instead of Groq; the live interview conversation,
  question selection, guardrail, and harness generation all stay on Groq,
  unchanged. Required `reasoning_effort="minimal"` since gpt-5-mini is a
  reasoning-family model that otherwise silently burns its whole token
  budget on hidden reasoning before writing visible output.

## Open items

Carried forward, not yet picked up:

- **`deploy.sh` still references the retired Piston container** —
  `PISTON_INTERNAL`/`PISTON_IMAGE` variables and a `greenroom-piston.internal`
  URL are still set and passed through, inconsistent with this week's Judge0
  migration (the GitHub Actions CI/CD pipeline is the actual live deploy
  path; unclear if `deploy.sh` is still used or itself leftover — worth
  confirming and either updating or removing it).
- **Leftover self-hosted-Piston config** — the `piston/` directory
  (Dockerfile, fly.toml, install script) and the `piston/**` CI trigger path
  are dead weight after this week's Judge0 migration; not yet deleted.
- **`infra/monitoring.bicep`'s planned metrics still reference "Piston vs
  Wandbox"** — needs updating to the current Judge0-tier split (public /
  RapidAPI / local subprocess) before that dashboard is deployed.
- **Reliance on Judge0's public instance has no SLA** — observed directly
  this week (transient rate-limiting during rapid test calls). RapidAPI
  fallback and local-subprocess last resort exist, but there's no monitoring
  yet on how often each tier is actually hit in production (see the Piston
  vs Wandbox metrics item above, once renamed).
- **`test_delete_session_success_when_supabase_configured` has a stale
  assertion** — expects `delete_session` to only touch
  `evaluations`/`messages`/`sessions`, but the endpoint has deleted from
  `analytics_events` too since PR #29/#30; a one-line test fix, not yet done.

- **Remaining Java/C++ gap** — 28 (java) / 31 (cpp) of 218 non-stdio
  technical questions still have no working harness after both the
  dataset-first and LLM-fallback passes — mostly custom-type (tree/graph)
  or otherwise complex problems outside the deterministic driver's supported
  type vocabulary. A further swap round is possible but each one needs a
  hand-verified or LLM-verified reference solution; not attempted yet.
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
- ~~**Seniority/role differentiation**~~ — **done, 2026-08-04** (PR #45):
  `infer_seniority()` now weights question difficulty by the candidate's
  stated role. Formally out of scope as of v4.0 as a broader "different
  question sets per seniority" ask; only the difficulty-weighting slice has
  shipped, the rest remains unscoped if revisited.
- ~~**System-design and behavioral tracks are newly live in production —
  worth a manual smoke test**~~ — **done, 2026-08-04**: ran all three tracks
  end-to-end (5+ turns each) against the live backend/Supabase. Behavioral
  scored cleanly with full STAR analysis. System-design's topic-drift
  guardrail correctly caught and redirected an off-topic answer instead of
  silently scoring it — but the smoke test also surfaced the diagram-scoring
  gap and the question-bank call-signature bug documented above, both now
  fixed and re-verified.
