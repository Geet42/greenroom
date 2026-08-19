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

**2026-08-04 to 2026-08-19 — reliability/scale hardening, deployment pipeline overhaul, production observability, and several candidate-facing features**

- **Fixed `evaluate_session` crashing with "Failed to end session"** (`fc9e76d`) —
  gpt-5-mini burning its 700-token budget on hidden reasoning for long
  transcripts (raised to 4000/4000/2000 across `evaluate_session`,
  `_self_critique`, `evaluate_diagram`), plus an uncaught Ollama-fallback
  exception 500ing the whole request. Reproduced and verified against the
  real deployed Azure OpenAI config.
- **Question-bank audit/repair pipeline** (`61c32b7`, `c13ee5b`) — new
  `audit_question_bank.py` / `_deep_audit.py` (structural + content-level,
  read-only), `question_schema.py` (Pydantic contract), `harness_verify.py`
  (LLM-free compile check), and repair scripts. Found and fixed 74 questions
  with duplicate test cases; deleted 6 questions whose Java/C++/Node support
  resisted correct derivation rather than ship them unverified. Also fixed
  `generate_harness()` silently returning `None` for unsupported languages
  (masquerading as "no problem assigned") and a `seed_questions.py` upsert
  bug that would have silently nulled several columns on re-run.
- **Diagram-evaluation crash fixed** (`b66c2b7`) — unvalidated LLM JSON could
  fail `EndSessionResponse`'s strict schema on wording drift, 500ing the
  whole session-end call. `evaluate_diagram` now validates and derives
  `proximity_label` from `proximity_score` itself.
- **Sandbox output type crash + dead retry logic fixed** (`d097dfa`) — any
  problem whose harness returned a non-string scalar 500'd `/code/test`;
  `piston._judge0()` was also swallowing transient failures instead of
  raising, so the retry wrapper never retried.
- **AI-driven job-description analysis for question selection** (`aea2f8b`) —
  `analyze_job_description()` extracts seniority/topics from JD text via one
  concurrent LLM call at session start; feeds into all three question
  pickers as an override/topic-weight signal. 25 new tests.
- **Candidate seniority selector + full LLM/product observability**
  (`0797d6c`) — explicit junior/mid/senior selector on session start;
  `services/metrics.py` (Prometheus counters for LLM latency/error/cost,
  guardrail triggers, code-execution outcomes, session funnel, evaluation
  scores); production `/metrics` scraping wired into the Grafana dashboard.
- **Request latency bounding + generation dedup** (`f725f78`) — explicit
  timeouts on the Groq/Azure clients (45s/60s); `services/singleflight.py`
  so two concurrent cache misses for the same key don't both trigger an LLM
  call.
- **Session duration countdown, expiry handling, turn-cap removal**
  (`6787211`) — replaced the flat 15-message turn cap with an absolute
  `SESSION_MAX_DURATION_MINUTES` (default 60) wall-clock cap, exposed as
  `expires_at`; frontend countdown auto-triggers `/end` on expiry instead of
  a "lost connection" message.
- **Load-test-driven concurrency fixes** (`bab58da`, `b3a9462`, `368686a`,
  `6c4e62d`) — a 50-VU k6 run against production found and fixed, in order:
  blocking Postgres calls freezing the event loop (77.9% failure rate, p95
  11.3s), unpooled Groq/HTTP connections exhausting the container's DNS
  resolver, and Groq's real 30 RPM account ceiling being hit blind on every
  request. Added a shared cross-replica Groq request budget
  (`groq_budget_available()`), fixed a nil-UUID sentinel bug that let it
  silently degrade to a weaker per-replica fallback, and fixed a real
  test-credential leak into the live `rate_limit_events` table found along
  the way.
- **k6 load tests + Judge0 health-check hammering fixed** (`bcd7229`) —
  `infra/loadtest/` (17,226 requests/3min, 0% errors, p95 274ms post-fix);
  found `/api/health` hitting Judge0's public API on every single probe,
  now cached 30s.
- **Model benchmarking harness** (`d915422`) — `benchmark_models.py` +
  `data/model_rates.json`; surfaced that the real configured
  `FALLBACK_MODEL` is `gpt-oss:20b` (not the `llama3.3:70b` code default)
  and runs 3-5x slower than Groq.
- **"Industry-grade" deployment pipeline** (`7a6e446`) — deploy now gates on
  CI succeeding (`workflow_run`) instead of racing it independently; added
  post-deploy health verification with automatic rollback, Trivy container
  scanning + `pip-audit`/`npm audit` (both non-blocking), and Dependabot.
  Deliberately left the Azure auth mechanism as a stored `AZURE_CREDENTIALS`
  secret rather than migrate to unverified OIDC config on the live pipeline
  — migration path documented in `DEPLOYMENT.md` instead.
- **CI/CD unbroken, production logs wired into Grafana, mobile-responsive
  UI** (`dfa3e42`) — `deploy-containers.yml` had been failing every run
  since the Judge0 migration (building from a deleted `piston/` context);
  fixed, along with 17 pre-existing ruff errors that were failing the lint
  gate independent of any app change. Added the actual production log path
  to Grafana (Azure Monitor Log Analytics via KQL — local Loki/Promtail
  only ever sees Docker-local traffic, which Container Apps doesn't expose)
  and reorganized the dashboard into 6 labeled sections. Added a real
  mobile layout (hamburger nav, un-clipped stacked technical/system-design
  panels, scrollable session table).
- **Getting the Grafana production-logs panel actually working** (`6a7269d`
  through `28378c8`) — a live active-interviews panel; then five follow-up
  fixes to get the Azure Monitor KQL panel rendering real data: a duplicate
  panel id, a missing Log Analytics workspace resource reference, an
  unbounded query hitting the 30,000-row cap, and finally the correct KQL
  idiom (`tostring(parsed.user_id) in ($user_id)`) for the `$user_id`
  filter after two other quoting approaches both produced malformed
  queries.
- **CI/CD deploy-blocking fixes** (`e01f1c9`, `9884c4f`, `3ac75d9`) — the
  Trivy scan step referenced a nonexistent tag, then a tag whose own
  transitive action dependency no longer existed, then lacked the
  `security-events: write` permission its SARIF upload needed — each one
  blocked every deploy until fixed.
- **LeetCode-style layout for technical and system-design** (`7d55aeb`,
  `3ffbeaa`) — real problem-panel real estate instead of a cramped top
  strip; a redesigned results console; system-design gained the same
  layout plus previously-drafted-but-unused functional/non-functional
  requirements fields, and a viewport-height fix that had been clipping
  Excalidraw's toolbar with no way to reach it.
- **System-design UX parity fixes** — candidate-requested question
  switching now works on system-design, not just technical (`8806bb5`);
  Excalidraw's library sidebar replaced with a single inline shape strip
  (`ca934bf`); labeled architecture-component shapes added to the canvas
  (`dfe407f`).
- **Dashboard question difficulty/topic breakdown + avg session duration**
  (`bf3d2e2`); **structured `scale_metadata` tags for system-design
  questions** (`0de779b`); **page-view tracking** (`bd45d22`).
- **Removed the unused Piston Container App and deploy steps entirely**
  (`796ae82`) — it had zero real traffic since the Judge0 migration but was
  still being built/deployed every push; deleted from Azure along with
  `deploy.sh`'s Piston steps and the `piston/` directory.

## Open items

Carried forward, not yet picked up:

- **CI/CD authenticates to Azure with a stored `AZURE_CREDENTIALS` secret,
  not OIDC federated identity** — `DEPLOYMENT.md` documents the OIDC
  migration path (which secrets to add, the workflow diff, the order of
  operations), but whether the federated credential is actually configured
  in Azure AD is unconfirmed, so it hasn't been executed against the live
  pipeline. Also update `DESIGN.md` if this ever gets flipped again — it's
  been documented as OIDC before while the code ran on a stored secret.
- **`infra/monitoring.bicep` + `infra/deploy-monitoring.sh` are drafted but
  not deployed** — Log Analytics workspace, Application Insights, 5xx/
  restart/high-CPU alerts on all Container Apps. Needs `environmentId`/
  alert-email filled in, a `what-if` review, and the metric names
  double-checked against the live resource before applying.
- **No monitoring yet on how often each Judge0 tier (public / RapidAPI /
  local subprocess) is actually hit in production** — the tier split is
  logged per-request via `services/metrics.py` but not yet surfaced as a
  Grafana panel.
- **`test_delete_session_success_when_supabase_configured` has a stale
  assertion** — expects `delete_session` to only touch
  `evaluations`/`messages`/`sessions`, but the endpoint has deleted from
  `analytics_events` too since PR #29/#30; a one-line test fix, not yet done.
- **`infra/loadtest/interview_flow.js` is written but hasn't been run** — it
  exercises the actually expensive LLM/Judge0 path (`health_baseline.js`
  has been run repeatedly); needs a live Supabase auth token to execute.
- **Remaining Java/C++ gap, count not re-measured since the 2026-08-19
  content-audit pass** — as of 2026-08-04: 28 (java) / 31 (cpp) of 218
  non-stdio technical questions had no working harness after both the
  dataset-first and LLM-fallback passes, mostly custom-type (tree/graph)
  problems outside the deterministic driver's supported type vocabulary. A
  later audit pass (`c13ee5b`) removed 6 separate irreparable questions from
  the bank entirely, but the exact current unsupported count for the
  remaining 351-question bank hasn't been re-measured against live
  Supabase. A further swap round is possible but each one needs a
  hand-verified or LLM-verified reference solution; not attempted yet.
- **Human-vs-bot evaluation-score correlation study** — no data yet on
  whether `overall_score` actually agrees with a human interviewer's rating
  (see `docs/EVALUATION_METRICS.md` §2). Needs 30+ real transcripts before it
  can start.
- **Operational metrics now instrumented but not yet backfilled/analyzed** —
  `services/metrics.py` (added 2026-08-11/2026-08-14) gives live P50/P95
  latency, LLM fallback rate, guardrail trigger rate, and cost-per-session
  going forward, closing the gaps `docs/EVALUATION_METRICS.md` §7 listed as
  unmeasurable — but no one has yet pulled a real report out of it, and
  `docs/EVALUATION_METRICS.md` itself still describes the pre-instrumentation
  state as of 2026-07-30 (see note at the top of that file).
- ~~**`deploy.sh` still references the retired Piston container**~~ — **done**:
  `deploy.sh`'s Piston build/push/deploy steps and `PISTON_URL` were removed,
  and the `piston/` directory (Dockerfile, entrypoint scripts, old
  `fly.toml`) was deleted from the repo (`796ae82`).
- ~~**`infra/monitoring.bicep`'s planned metrics referenced "Piston vs
  Wandbox"**~~ — **done**: updated to note Judge0 is the current execution
  backend and the Piston app is no longer monitored (`dfa3e42`).
- ~~**Seniority/role differentiation**~~ — **done, 2026-08-04** (PR #45),
  **extended 2026-08-14/2026-08-17**: `infer_seniority()` weights question
  difficulty by the candidate's stated role; an explicit junior/mid/senior
  selector on session start (`0797d6c`) and JD-derived topic weighting
  (`aea2f8b`) were added on top of it. Formally out of scope as of v4.0 as a
  broader "different question sets per seniority" ask (as opposed to
  difficulty-weighting the existing bank) — that broader ask remains
  unscoped if revisited.
- ~~**System-design and behavioral tracks are newly live in production —
  worth a manual smoke test**~~ — **done, 2026-08-04**: ran all three tracks
  end-to-end (5+ turns each) against the live backend/Supabase. Behavioral
  scored cleanly with full STAR analysis. System-design's topic-drift
  guardrail correctly caught and redirected an off-topic answer instead of
  silently scoring it — but the smoke test also surfaced the diagram-scoring
  gap and the question-bank call-signature bug documented above, both now
  fixed and re-verified.
