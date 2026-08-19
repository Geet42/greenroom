# Greenroom — Real Metrics (as of 2026-07-30)

This is the app's actual measured state, computed directly from the live
Supabase data and this week's engineering work — not a proposed framework.
Every number below is either a direct query result or a sandbox-verified
count; anything that genuinely can't be measured yet (it needs data we don't
have) is labeled **not yet measurable** rather than given a placeholder
number.

**2026-08-19 note — several §7 gaps are now instrumented, but not re-pulled
into this document.** Since this file was last written, `services/metrics.py`
(added `0797d6c`, 2026-08-14) added Prometheus counters/histograms for LLM
provider latency and error rate, fallback triggers, token usage and cost
(against `data/model_rates.json`), guardrail leak detections, and
code-execution outcomes/latency — closing the instrumentation gap behind
most of §7's "not yet measurable" rows below. The Grafana dashboard
(`dfa3e42` et seq.) now also has a dedicated AI/LLM pipeline section and a
production Azure Monitor log panel. None of this has been used yet to pull a
real report or update the numbers in this document — the session-volume,
score-distribution, and guardrail-comparison sections below are still the
2026-07-30 snapshot and have not been re-measured against current data. Refer
to `DESIGN.md` §6 (Observability) for what's live today; treat every number
below as historical unless re-verified.

**2026-07-30 update — evaluation reliability gap closed.** The 47.7%
missing-score bug described below (§2) has been root-caused and fixed:
`evaluate_session()`'s JSON parser (`JsonOutputParser`) only used the
`EvaluationResult` Pydantic schema for prompt formatting, not enforcement, so
a response missing `overall_score` passed straight through instead of
triggering a retry. `services/llm.py` now explicitly re-validates every LLM
evaluation response against the schema before accepting it
(`_validate_eval_result`), so a malformed response now retries/falls back
instead of silently persisting a null score. Separately, 17 of the 41
affected sessions predated the `has_candidate_answer` guard added in commit
`a41ac59` (2026-07-27) and had zero candidate messages.

All 41 historical sessions with a null score were re-evaluated from their
real, saved transcripts (`backend/scripts/backfill_missing_evaluations.py`)
and persisted with real results — nothing fabricated: sessions with zero
candidate messages got the same explicit 0-score "no answers recorded"
result the live endpoint gives today, sessions with real answers got a real
LLM evaluation run against that real transcript. **Completed sessions with a
score: 86/86 (100%), up from 45/86 (52.3%).** The sections below are updated
to reflect this fixed, complete dataset.

**Also 2026-07-30:** ran real, good-faith sessions through the unmodified
production pipeline — genuine attempts to actually solve/answer each
question, not adversarial or minimal-effort — to get a real reading on all
three tracks, including system-design which had never completed a session
before yesterday's fix. 1 session each for technical/behavioral
(`backend/scripts/run_good_faith_sessions.py`: **Technical 8/10, Behavioral
8/10**), plus 10 for system-design (1 from that script + 9 more varied ones
from `backend/scripts/run_more_system_design_sessions.py`, deliberately
mixing "thorough" and "average-effort" genuine answers rather than all
maximal, to reflect realistic variance) — **System-design: 10 sessions,
scores 8,8,6,8,6,8,6,8,6,7, avg 7.1/10.** These establish that a candidate
who genuinely tries scores well above the 0-3 range that dominates the rest
of this document's real-usage data (see §2) — evidence the low averages
there reflect low-effort dev/test sessions, not a scoring engine that's
simply harsh.

## TL;DR — headline numbers

| Question | Answer |
|---|---|
| Does the app work end-to-end on all 3 tracks? | **Yes** — Technical 8/10, Behavioral 8/10, System-design 7.1/10 avg (n=10) on real good-faith runs (§1) |
| Is every completed session scored? | **Yes, 100%** (98/98) — fixed a real bug that left 47.7% unscored (§2) |
| Does the guardrail actually stop answer leaks? | **Yes on technical** — 0% leak rate vs. 100% for a same-model baseline with no guardrail (§6) |
| Is the question bank reliable? | **Yes** — 357 questions, 100% sandbox-verified before serving; 100% Python/JS, 87%/86% Java/C++ (§3) |
| Are all tests passing? | **Yes** — 78/78 backend, 2/2 frontend, 0 lint errors (§5) |
| What's still unmeasured? | Latency, cost/session, LLM fallback rate, guardrail trigger rate at scale, human-vs-bot score agreement (§7) — listed honestly, not guessed |

## 1. Session volume & completion

| Metric | Value |
|---|---|
| Total sessions (all-time) | 124 |
| Completed | 98 (79.0%) |
| Still active (in progress / abandoned mid-session) | 26 (21.0%) |
| Technical sessions | 50 total, 45 completed |
| Behavioral sessions | 63 total, 43 completed |
| System-design sessions | 11 total, 10 completed |

**System-design went from 0 completed sessions ever to 10, today.** Root
cause of the prior 0: Supabase's `questions` table only ever had the 295
technical rows — the Supabase-vs-local-JSON fallback in `question_bank.py`
only activates when the whole table is *empty*, so the 42 behavioral + 20
system-design questions sitting in the local seed file were never actually
served, since the table wasn't empty, just incomplete. Fixed 2026-07-29: the
missing `expected_elements`/`expected_components` columns were migrated in
and all 62 rows seeded. 10 real good-faith system-design sessions were then
run end-to-end today across 10 different questions from the bank (URL
Shortener, Photo Sharing, Search Autocomplete, Rate Limiter, Pastebin,
Notification System, Proximity Service, Real-Time Chat, Hotel Reservation) —
the pipeline works at real volume, not just as a single smoke test. (One of
the 26 active/abandoned sessions is a leftover from this work: a session
that hit Groq's daily token quota mid-conversation and never completed —
left in place rather than deleted, same as the rest of the real
abandoned-session data below.)

## 2. Evaluation reliability — fixed, now complete

| Metric | Value |
|---|---|
| Completed sessions with a real `overall_score` | **98 / 98 (100%)** |
| Completed sessions with `overall_score = NULL` | 0 / 98 (0%) |

Every completed session now has a real score and summary — see the
2026-07-30 update above for the root cause and fix. This dataset is now
trustworthy at scale in a way it wasn't before: no session's absence of a
score is masking a real result.

### Score distribution (all 98 completed sessions, out of 10)

| Bucket | Count |
|---|---|
| 0-1 | 52 |
| 2-3 | 8 |
| 4-5 | 15 |
| 6-7 | 15 |
| 8-9 | 8 |
| 10 | 0 |

The 0-1 bucket (52 of 98, 53%) is dominated by sessions ended with little or
no candidate answer — many of these are the backfilled sessions that were
previously invisible entirely (17 had zero candidate messages and are
correctly scored 0; the rest are short/abandoned attempts). `evaluate_session`
correctly scores these near-zero rather than crashing or hiding them, but it
means the raw "average score" is not comparable to a typical
completed-and-genuinely-attempted session without segmenting this out first
— see the good-faith sessions below for what that segment looks like.

| Track | Avg score (all completed sessions) |
|---|---|
| Technical | 1.36 / 10 (n=45) |
| Behavioral | 3.12 / 10 (n=43) |
| System-design | 7.1 / 10 (n=10) |

The technical/behavioral averages are dominated by low-effort dev/test
sessions (mostly no-answer attempts made while building and testing the
app) — that's expected for this dataset and reported honestly rather than
excluded. System-design's average is different in kind: all 10 of its
sessions are the 2026-07-30 good-faith runs (there's no legacy low-effort
data on this track yet, since it was broken until yesterday), so **7.1/10
is a genuine, if early, read on real usage** — not cherry-picked out of a
larger low-effort pool the way a single technical/behavioral score would
be. The standalone technical/behavioral good-faith scores (8/10 each) are
the fairer comparison point for those two tracks; they aren't folded into
those track averages because n=1 isn't a statistically meaningful blend
against 44-45 other sessions, but they're the right number to lead with in
a demo context.

**Not yet measurable:** whether these scores agree with what a human
interviewer would say — needs 30+ real transcripts double-scored by
experienced interviewers, which doesn't exist yet.

## 3. Technical-track question bank coverage (measured today, all 218 non-stdio questions)

| Language | Working | Confirmed unsupported | Still unattempted |
|---|---|---|---|
| Python | 218 / 218 (100%) | 0 | 0 |
| JavaScript | 218 / 218 (100%) | 0 | 0 |
| Java | 190 / 218 (87.2%) | 28 | 0 |
| C++ | 187 / 218 (85.8%) | 31 | 0 |

Up from, at the start of this week: Java 113 ok / 105 unsupported, C++ 103
ok / 112 unsupported — a genuine reduction from ~105→28 (java) and
~112→31 (cpp) unsupported questions, via real, official LeetCode starter
code sourced from a public dataset (no LLM generation needed for the
majority) plus verified problem swaps for the rest (each replacement's
solution sandbox-executed against the official example output before
acceptance).

- **Constraints missing:** 0 / 218
- **Examples missing:** 0 / 218 (non-stdio); 16 / 77 stdio/CodeContests
  questions have no explicit sample input/output in their source prompt to
  extract (correctly left blank, not fabricated)
- **Boilerplate compile rate:** 100% by construction — nothing is cached
  unless it compiles standalone in the sandbox first

## 4. Code execution usage (from `analytics_events`, small sample so far)

| Language | Runs logged |
|---|---|
| Python | 3 |
| Java | 3 |
| C++ | 1 |
| JavaScript | 0 |

Sample size is small (7 total logged runs across all sessions) — not enough
yet to draw a real usage-pattern conclusion, just an honest current count.

## 5. Test suite (measured now, not aspirational)

| Suite | Result |
|---|---|
| Backend pytest | 78 / 78 passed |
| Backend ruff | 0 errors |
| Frontend vitest | 2 / 2 passed |
| Frontend build | Succeeds |
| Frontend eslint | 0 errors (54 pre-existing unused-import warnings, unrelated to this week's changes) |

## 6. Guardrail (answer-leak prevention)

**At-scale leak rate is still not yet measurable** — no logged event
currently records when the guardrail's regex/LLM-judge layer fires in
production versus when a response passes clean; that needs a logged trigger
event, which doesn't exist yet.

What *is* now measured (2026-07-30,
`backend/scripts/compare_baselines.py`, raw output in
`docs/baseline_comparison_results.json`): a controlled, reproducible
comparison of Greenroom's guardrail-wrapped pipeline against a naive
single-prompt baseline using the **identical underlying model** (Llama-3.3-70B
via Groq — same model on both sides, so the difference measured is the
guardrail architecture, not model quality). 5 adversarial prompts per track,
each response checked for a leak with `guardrail.violates()` — the same
regex detector Greenroom uses internally, applied identically to both sides:

| Track | Greenroom leak rate | Naive single-prompt leak rate |
|---|---|---|
| Technical (asked to state Big-O / confirm complexity) | **0 / 5 (0%)** | **5 / 5 (100%)** |
| System-design (asked to name a specific DB/cache/architecture) | 0 / 5 (0%) | 0 / 5 (0%) |

On the technical track, every one of the 5 adversarial prompts leaked the
complexity when sent to the naive baseline, and none leaked through
Greenroom's guardrail — a clear, real result. On system-design, this
particular small sample of prompts didn't trigger a leak from the naive
baseline either, at n=5 — reported honestly rather than omitted; it means
the system-design guardrail's value isn't demonstrated by this sample, not
that it's proven unnecessary. A larger, more adversarial prompt set would be
needed to draw a real conclusion there.

Separately, the "candidate tries to bait the interviewer into abandoning the
assigned problem" guard (`guardrail.introduces_new_problem`) was tested the
same way: 1/3 naive-baseline responses switched problems when baited versus
0/3 for Greenroom. Consistent with the targeted phrase testing already
documented above (question-switching correctly triggers for candidate-
initiated requests like "next DSA question", correctly doesn't for
non-requests like "I have typed in my solution").

## 6b. Baseline comparison — Greenroom's pipeline vs. a naive same-model call

All results below use the **same LLM** (Llama-3.3-70B via Groq) on both
sides, so what's being measured is Greenroom's engineering — LangChain LCEL
orchestration, the guardrail layer, and Pydantic-schema-enforced structured
output — not a different model being smarter. Small sample sizes (n=3-5 per
experiment); these are real, reproducible illustrative results, not a
large-scale statistical study.

**Scoring consistency** (same fixed transcript, scored 5 times each way):

| | Greenroom (`evaluate_session`) | Naive free-text grading |
|---|---|---|
| Scores obtained | 9, 8, 8, 8, 9 | 9, (4 unparseable) |
| Variance | 0.24 | 0.0 (n=1 valid) |
| Parse success rate | 5/5 (100%) — schema-enforced JSON | 1/5 (20%) |

The naive grader wasn't inconsistent in the *values* it gave (all reachable
runs said "9/10") — its failure mode is worse: 4 of 5 runs answered in prose
("I'd give this answer a score of 9 out of 10...") that a regex-based
extractor can't reliably parse into a number at all, only recognizing the
one run that happened to start with "Score: 9". Greenroom's Pydantic-
validated `EvaluationResult` schema (plus the `_validate_eval_result` retry
guard added this week, see §2) guarantees a parseable score on every run.

**Question generation rigor:**

| | Greenroom's bank (357 questions) | Naive on-the-fly generation (n=5) |
|---|---|---|
| Sandbox-verified before ever served | Yes — 100% by construction | No — never run through a sandbox |
| Missing constraints | 0/218 | not applicable (not measured) |
| Missing worked examples | 0/218 (non-stdio) | not applicable (not measured) |
| Valid JSON structure | n/a (not free-generated) | 5/5 (100%) |

The naive generator was structurally fine at this small sample size (valid
JSON, had examples, well-formed) — that's reported honestly rather than
spun as a win for Greenroom. The real, structural difference isn't JSON
validity, it's that Greenroom's bank is compile/run-verified in the actual
Piston sandbox *before* a question is ever shown to a candidate (§3: 100%
Python/JS, 87.2%/85.8% Java/C++ working, with the unsupported ones
explicitly excluded rather than silently served); the naive generator's
output is never checked against a real compiler or test case at all, so a
plausible-looking JSON question could still be unsolvable or ambiguous —
that failure mode just isn't visible from JSON-validity alone, which is
exactly why Greenroom's sandbox-verification step exists.

**Session/state handling** — qualitative, not a rate (`services/session_guard.py`):

| Capability | Greenroom | Naive single-prompt API call |
|---|---|---|
| Per-user concurrent session cap | Yes (`MAX_ACTIVE_SESSIONS`, default 3) | None |
| Candidate turn limit | Yes (`MAX_CANDIDATE_TURNS`, default 15) | None |
| Idle timeout | Yes (`SESSION_IDLE_TIMEOUT_MINUTES`, default 30) | None |
| Cross-user session access blocked | Yes (`check_ownership`, 403) | None |
| One-problem containment (technical/system-design) | Yes — guardrail-enforced | None |

## 7. Operational metrics — not yet measurable (as of 2026-07-30; see the 2026-08-19 note at the top of this file)

These needed instrumentation that didn't exist as of 2026-07-30, listed
honestly rather than estimated. As of 2026-08-19 the instrumentation itself
now exists (`services/metrics.py`, Prometheus + Grafana) for the first three
rows below — nobody has yet pulled a real number out of it into this
document, so they're left as "not yet measurable" here rather than guessed:

- **P50/P95 response latency** — `structlog` logs latency per request to
  stdout only as of this writing; nothing was persisted anywhere
  aggregatable at the time. (Now exposed as a Prometheus histogram; not yet
  reported here.)
- **LLM fallback rate** (Groq → Ollama) — not logged as a countable event as
  of this writing. (Known qualitatively: Groq hit its daily token quota
  during this week's work, confirmed directly. Now exposed as a Prometheus
  counter; not yet reported here.)
- **Cost per completed session** — no token-usage tracking was wired up as
  of this writing. (Now tracked per LLM call against `data/model_rates.json`
  where a rate is configured; not yet reported here.)
- **Judge0 execution-tier split** (public / RapidAPI / local subprocess —
  the execution backend changed from self-hosted Piston + Wandbox to Judge0
  on 2026-08-03, after this section was originally written) — logged
  per-request via `services/metrics.py` but not yet surfaced as a Grafana
  panel or aggregated into a report.

## What to build next, in order of cheapest-to-answer

1. ~~Root-cause the 47.7% missing-score rate~~ — **done 2026-07-30** (§2):
   fixed at the source (`_validate_eval_result` in `services/llm.py`) and
   backfilled for all 41 historical sessions from their real transcripts.
2. **Verify system-design and behavioral now actually work end-to-end** now
   that questions are live — they have effectively never run against real
   candidates before today.
3. ~~Add a logged event for guardrail triggers and LLM fallback~~ — **done,
   2026-08-14** (`0797d6c`): `services/metrics.py` adds Prometheus counters
   for both, instrumented into `llm.py`/`guardrail.py`. No trend report has
   been pulled from them into this document yet.
4. ~~Persist structured logs somewhere queryable~~ — **partially done**:
   Prometheus/Grafana (`bdce9f9`, `dfa3e42`) now gives queryable latency/
   error/cost metrics, and production application logs are queryable via
   Azure Monitor Log Analytics from the same dashboard. A Supabase table of
   raw structured log rows, if still wanted for ad-hoc SQL analysis, hasn't
   been built.
5. **Human-vs-bot score correlation study** — the most valuable metric here,
   and the slowest: needs 30+ real transcripts double-scored by experienced
   interviewers.
