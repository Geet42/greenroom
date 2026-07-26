# Evaluating Greenroom against industry mock-interview tools

This is a proposed measurement framework, not implemented telemetry — it defines
*what* to track and *why* so it can be instrumented incrementally (start with
the "cheap, do now" tier below, add the rest as it proves useful).

Industry mock-interview products (Pramp, interviewing.io, LeetCode's own AI
interviewer, Voomer, etc.) mostly compete on three axes: **does it understand
what you actually said**, **is the feedback something a real interviewer would
also say**, and **does it feel reliable enough to trust for practice**. The
metrics below map to those three axes plus the operational cost of running it.

## 1. Context & comprehension accuracy

This is the thing an LLM interviewer can silently get wrong: losing track of
what the candidate already said, or asking a question that ignores an answer
they just gave.

| Metric | How to measure | Target |
|---|---|---|
| **Follow-up relevance** | Sample N transcripts; have a human (or a separate, stronger LLM-as-judge) rate each interviewer turn 1-5 on "does this follow from the candidate's last answer" | ≥4.2/5 avg |
| **Repetition rate** | % of interviewer turns that re-ask something already answered in `history` | <2% |
| **Assigned-question consistency** | For technical/system-design: does the interviewer's spoken question match `assigned_question` in `SESSIONS`? (a code bug here is directly testable, not just LLM judgment) | 100% (regression-testable) |
| **Guardrail leak rate** | % of sessions where the interviewer accidentally reveals the answer/solution (the four-layer guardrail already exists per `DESIGN.md`) — spot-check via keyword match against the assigned question's solution, then human-review flags | <0.5% |

**Cheap, do now:** log `(session_id, turn_index, assigned_question_id)` as an
analytics event already flowing through `POST /analytics/event` — this alone
lets you build the "assigned-question consistency" metric and repetition-rate
metric with a SQL query against `messages`, no new instrumentation needed.

## 2. Evaluation accuracy (does the score mean anything)

The current pipeline is a single LLM pass optionally self-critiqued
(`EVAL_SELF_CRITIQUE_ENABLED`, `services/llm.py:389`). The risk with any
LLM-graded score is **construct validity** — does a 7/10 actually correlate
with something real.

| Metric | How to measure | Target |
|---|---|---|
| **Inter-rater agreement (LLM vs human)** | Collect 30-50 real transcripts, have 2-3 experienced interviewers score them blind on the same rubric, compare to the bot's `overall_score` (Pearson correlation or Cohen's kappa on bucketed scores) | r ≥ 0.7 |
| **Self-critique disagreement rate** | % of sessions where the critique pass (`EVAL_SELF_CRITIQUE_ENABLED`) changes the score by >1 point — a proxy for how often the first pass was shaky | track trend, no fixed target |
| **Score stability** | Re-run `evaluate_session` on the same transcript 3x (temperature>0 means it varies) — stdev of `overall_score` | ≤0.5 points |
| **STAR-element detection precision/recall** | For behavioral: does `star_analysis.missing_elements` actually match what's missing, per human review of a sample | precision & recall ≥0.8 |

**Cheap, do now:** score stability (#3) is a pure backend test — no human
labeling needed, run it in CI against a handful of frozen transcripts as a
regression check that the evaluation prompt hasn't drifted.

## 3. Technical-track correctness (uniquely testable, not LLM-judged)

Unlike the conversational tracks, technical-track code execution is fully
deterministic and now has real automated coverage after this session's fixes:

| Metric | How to measure | Target |
|---|---|---|
| **Boilerplate compile rate** | % of `(question, language)` pairs where `get_or_generate`/`get_or_generate_signature` produces boilerplate that compiles as-is (now enforced by `_compiles()` in `harness_generator.py`) | 100% by construction (rejected otherwise) |
| **Harness verification pass rate** | % of `(question, language)` generation attempts where the reference solution passes all tests on first try | track trend — this session found ~40-60% first-try pass rate for Java/C++ on a small sample; low rates mean the harness-gen prompt needs work |
| **Test-runner false-fail rate** | % of *known-correct* reference solutions that fail the harness due to a harness bug, not a solution bug (distinguish via manual review of failures) | <5% |

**Cheap, do now:** add a scheduled job (weekly GitHub Action) that runs
`get_or_generate`/`get_or_generate_signature` against every bank question
that doesn't have cached java/cpp harnesses yet, and reports the pass rate —
turns the "does this even work" question from a support ticket into a graph.

## 4. Operational / cost metrics (what industry tools also report)

| Metric | Source | Why it matters |
|---|---|---|
| **P50/P95 response latency** (interviewer turn, code run, TTS) | Already loggable from `services/logger.py`'s structured `http.request` events — needs latency histograms, not just per-request logs | Candidate-facing "does this feel snappy" |
| **LLM fallback rate** (Groq → Ollama fallback triggered) | `services/llm.py` fallback path — add a log event when it fires | High rate = primary provider reliability problem |
| **Cost per completed session** | Token usage × Groq/fallback pricing, divided by completed sessions | Lets you compare "cost per mock interview" against what Pramp/interviewing.io charge human interviewers for the same thing |
| **Session completion rate** | `sessions.status = 'completed'` ÷ `sessions.status IN ('completed','active')` — now directly meaningful since this session's fixes made "active" reliably mean "actually still in progress" | Low completion = friction somewhere in the flow (this is exactly what bugs 7-9 were causing before this session's fixes) |

## Suggested rollout order

1. **Now, no new code**: SQL-query the metrics that are already derivable from
   existing `messages`/`sessions`/`analytics_events` tables (assigned-question
   consistency, session completion rate, guardrail spot-checks).
2. **Next**: the weekly harness-generation health-check job (#3) — cheapest
   automatable signal, directly informs whether the LLM-generation approach in
   `harness_generator.py` needs prompt work.
3. **When you have 30+ real sessions**: the human-vs-LLM scoring correlation
   study (#2) — this is the one metric that actually tells you if the product
   is trustworthy, but it needs real transcripts and human time, so it's the
   slowest to start.
