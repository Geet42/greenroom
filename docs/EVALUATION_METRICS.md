# Greenroom — Real Metrics (as of 2026-07-29)

This is the app's actual measured state, computed directly from the live
Supabase data and this week's engineering work — not a proposed framework.
Every number below is either a direct query result or a sandbox-verified
count; anything that genuinely can't be measured yet (it needs data we don't
have) is labeled **not yet measurable** rather than given a placeholder
number.

## 1. Session volume & completion

| Metric | Value |
|---|---|
| Total sessions (all-time) | 110 |
| Completed | 86 (78.2%) |
| Still active (in progress / abandoned mid-session) | 24 (21.8%) |
| Technical sessions | 49 total, 44 completed |
| Behavioral sessions | 61 total, 42 completed |
| System-design sessions | 0 |

**System-design has never completed a single session.** Root cause found
this week: Supabase's `questions` table only ever had the 295 technical
rows — the Supabase-vs-local-JSON fallback in `question_bank.py` only
activates when the whole table is *empty*, so the 42 behavioral + 20
system-design questions sitting in the local seed file were never actually
served, since the table wasn't empty, just incomplete. Fixed 2026-07-29: the
missing `expected_elements`/`expected_components` columns were migrated in
and all 62 rows seeded. System-design sessions have not been possible to
complete until today's fix — the 0 above reflects the broken period, not a
UX or evaluation problem.

## 2. Evaluation reliability — a real, uncomfortable number

| Metric | Value |
|---|---|
| Completed sessions with a real `overall_score` | 45 / 86 (52.3%) |
| Completed sessions with `overall_score = NULL` and empty summary | **41 / 86 (47.7%)** |

Nearly half of all "completed" sessions have no score and no summary at
all — `evaluate_session()` either failed silently or was never invoked for
these. This is not a construct-validity question (does the score mean
anything) — it's more basic: **the score frequently doesn't exist at all.**
This is the single most important reliability gap this data surfaces, and it
should be root-caused before anything else in this document is treated as
trustworthy at scale.

### Score distribution (the 45 sessions that do have a score, out of 10)

| Bucket | Count |
|---|---|
| 0-1 | 18 |
| 2-3 | 2 |
| 4-5 | 15 |
| 6-7 | 9 |
| 8-9 | 1 |

The 0-1 bucket (18 of 45, 40%) is dominated by sessions ended with little or
no candidate answer — `evaluate_session` correctly scores these near-zero
rather than crashing, but it means the "average score" number is not
comparable to a typical completed-and-tried session without segmenting this
out first.

| Track | Avg score (completed, non-null only) |
|---|---|
| Technical | 1.91 / 10 |
| Behavioral | 3.62 / 10 |

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

**Not yet measurable at scale** — no logged event currently records when the
guardrail's regex/LLM-judge layer fires versus when a response passes clean.
The mechanism exists and was extended this week (candidate-requested
question-switching had to be taught to bypass the "no second problem" rule
specifically, confirmed via targeted phrase testing — "next DSA question",
"can i have next dsa question", etc. all correctly trigger it; "i have typed
in my solution" correctly does not) — but a real leak-rate percentage needs
a logged trigger event, which doesn't exist yet.

## 7. Operational metrics — not yet measurable

These need instrumentation that doesn't exist yet, listed honestly rather
than estimated:

- **P50/P95 response latency** — `structlog` logs latency per request to
  stdout only; nothing is persisted anywhere aggregatable yet.
- **LLM fallback rate** (Groq → Ollama) — not currently logged as a
  countable event. (Known qualitatively: Groq hit its daily token quota
  during this week's work, confirmed directly.)
- **Cost per completed session** — no token-usage tracking wired up.
- **Piston vs Wandbox execution split** — logged per-request but not
  aggregated anywhere queryable; the self-hosted Piston sandbox has been
  unreachable for the entirety of this week's local testing, with every
  real execution falling through to Wandbox.

## What to build next, in order of cheapest-to-answer

1. **Root-cause the 47.7% missing-score rate** (§2) — this is a bug, not a
   metrics gap, and it undermines every other evaluation number until fixed.
2. **Verify system-design and behavioral now actually work end-to-end** now
   that questions are live — they have effectively never run against real
   candidates before today.
3. **Add a logged event for guardrail triggers and LLM fallback** — both are
   one line of code at the point they already happen; today they leave no
   trace.
4. **Persist structured logs somewhere queryable** (even just a Supabase
   table) to make latency/cost numbers derivable without more instrumentation.
5. **Human-vs-bot score correlation study** — the most valuable metric here,
   and the slowest: needs 30+ real transcripts double-scored by experienced
   interviewers.
