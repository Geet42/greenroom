"""
Question bank — curated, verified technical interview problems with canonical
test cases (the file these came from, data/question_bank.json, is checked by
data/verify_question_bank.py against reference solutions, so every expected
value is actually correct rather than LLM-guessed).

Update path: this reads from a `questions` table in Supabase first, falling
back to the local JSON seed if that table is empty or unreachable. That means
the bank can grow or change at any time — add a row in Supabase — without a
backend redeploy. The local JSON file is only the bootstrap seed; the durable,
"keeps updating" copy lives in Supabase.
"""

from __future__ import annotations

import json
import os
import random
import re
import threading

from services.logger import log
from services.question_schema import classify_and_validate
from services.supabase_client import get_supabase

_CLASS_METHOD_PATTERN = re.compile(r"^(\w+)\(\)\.(\w+)$")


def parse_function_name(raw: str | None) -> tuple[str | None, str]:
    """Splits a question's function_name field into (class_name, method_name).

    Most entries are plain functions, e.g. "two_sum" -> (None, "two_sum").
    LeetCode-imported entries instead encode the calling convention as
    "Solution().methodName" -> ("Solution", "methodName") — that exact string
    is required verbatim by test_runner, which executes tests["call"] as-is
    (e.g. "Solution().longestPalindromicSubsequence(s='a', k=2)"), so it is
    NOT a data bug to fix — the class *is* part of how these are invoked.
    Callers that need to talk about the signature (the interviewer's phrasing,
    generated boilerplate) should use the parsed method_name instead of the
    raw field, since "Solution().methodName" is not a valid identifier on its
    own."""
    if not raw:
        return None, ""
    m = _CLASS_METHOD_PATTERN.match(raw)
    if m:
        return m.group(1), m.group(2)
    return None, raw

_SEED_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "question_bank.json")
_lock = threading.Lock()
_cache: list[dict] | None = None

_JUNIOR_KEYWORDS = ("junior", "jr.", "jr ", "entry", "intern", "associate", "new grad", "graduate", "trainee")
_SENIOR_KEYWORDS = ("senior", "sr.", "sr ", "staff", "principal", "lead", "architect", "distinguished")

# Difficulty mix per seniority tier — junior interviews skew easy with fewer
# mediums and no hards; senior interviews skew toward medium/hard and rarely
# open with easy. "mid" (the default, unlabeled role) stays close to the
# original uniform-ish behavior.
_DIFFICULTY_WEIGHTS = {
    "junior": {"easy": 0.65, "medium": 0.35, "hard": 0.0},
    "mid":    {"easy": 0.35, "medium": 0.45, "hard": 0.20},
    "senior": {"easy": 0.10, "medium": 0.45, "hard": 0.45},
}


def infer_seniority(role: str | None) -> str:
    """Buckets a free-text role string (e.g. "Junior Backend Engineer",
    "Staff Software Engineer") into "junior" | "mid" | "senior" so question
    selection can skew its difficulty mix accordingly. Defaults to "mid" for
    anything that doesn't mention a seniority keyword."""
    role_lower = (role or "").lower()
    if any(kw in role_lower for kw in _JUNIOR_KEYWORDS):
        return "junior"
    if any(kw in role_lower for kw in _SENIOR_KEYWORDS):
        return "senior"
    return "mid"


def _topic_matches_jd(topic: str | None, jd_topics: list[str] | None) -> bool:
    """Loose match between a bank question's short kebab-case topic tag
    (e.g. "dynamic-programming", "caching") and a free-text topic/keyword
    pulled from an AI reading of the job description (e.g. "distributed
    caching", "React"). Not exact NLP — just enough to bias selection
    toward JD-relevant questions, never a hard filter, so a miss only
    means "no boost," not "excluded"."""
    if not topic or not jd_topics:
        return False
    topic_norm = topic.replace("-", " ").lower()
    for jd_topic in jd_topics:
        jd_norm = jd_topic.lower()
        if topic_norm in jd_norm or jd_norm in topic_norm:
            return True
        if topic_norm in jd_norm.split() or any(w == topic_norm for w in jd_norm.split()):
            return True
    return False


# Multiplier applied to a candidate's difficulty-based weight when its topic
# matches something the JD analysis flagged — tuned to noticeably skew
# selection toward JD-relevant questions without making non-matches
# unreachable (a session's bank may have few/no questions on a given topic).
_JD_TOPIC_BOOST = 3.0


def _weighted_choice(
    candidates: list[dict], seniority: str, jd_topics: list[str] | None = None,
) -> dict | None:
    """Picks one candidate, weighting by difficulty per _DIFFICULTY_WEIGHTS
    (with an extra boost for questions matching jd_topics, if given) instead
    of a flat random.choice — falls back to uniform choice if the weighted
    pool is empty (e.g. every candidate's difficulty has weight 0)."""
    if not candidates:
        return None
    weights = _DIFFICULTY_WEIGHTS[seniority]
    scored = []
    for c in candidates:
        w = weights.get(c.get("difficulty") or "medium", 0)
        if _topic_matches_jd(c.get("topic"), jd_topics):
            w = (w or 0.05) * _JD_TOPIC_BOOST  # a 0-weight difficulty can still surface if it's JD-relevant
        scored.append((c, w))
    total = sum(w for _, w in scored)
    if total <= 0:
        return random.choice(candidates)
    r = random.uniform(0, total)
    upto = 0.0
    for c, w in scored:
        upto += w
        if upto >= r:
            return c
    return scored[-1][0]


def _load_seed() -> list[dict]:
    with open(_SEED_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def _load_from_supabase() -> list[dict] | None:
    sb = get_supabase()
    if not sb:
        return None
    try:
        resp = sb.table("questions").select("*").execute()
        return resp.data or None
    except Exception as exc:
        log.error("question_bank.supabase_load_failed", error=str(exc))
        return None


def _warn_on_invalid_rows(rows: list[dict]) -> None:
    """Soft, log-only validation against services.question_schema — never
    drops or mutates a row, never raises. This is diagnostic only (the audit
    script, backend/scripts/audit_question_bank.py, is the authoritative,
    structured version of this same check); a malformed row still gets served
    exactly as before, just with a warning logged, matching this module's
    existing fail-open philosophy (Supabase -> seed fallback, None-returns
    treated as "not available" everywhere downstream)."""
    for row in rows:
        _, issues = classify_and_validate(row)
        if issues:
            log.warning(
                "question_bank.invalid_row",
                id=row.get("id"), track=row.get("track"),
                issues=[f"{i.field}: {i.message}" for i in issues],
            )


def _all_questions() -> list[dict]:
    """Cached for the life of the process; call refresh() to force a re-read
    (e.g. after editing the Supabase table) without restarting the backend."""
    global _cache
    with _lock:
        if _cache is None:
            _cache = _load_from_supabase() or _load_seed()
            _warn_on_invalid_rows(_cache)
        return _cache


def refresh() -> None:
    global _cache
    with _lock:
        _cache = None


def pick_question(
    track: str,
    language: str = "python",
    topic: str | None = None,
    difficulty: str | list[str] | None = None,
    exclude_ids: set[str] | None = None,
    role: str | None = None,
    jd_seniority: str | None = None,
    jd_topics: list[str] | None = None,
) -> dict | None:
    """Random question matching track/language(/topic/difficulty). None if nothing
    matches — callers should fall back to ad hoc LLM-generated problems in that case.

    difficulty defaults to ["easy", "medium"] — "hard" problems are excluded unless
    explicitly requested, since they're disproportionately represented in the
    imported LeetCodeDataset batch (71/210) and aren't a great default mock-interview
    experience, EXCEPT for senior roles (see `role` below), where hard is included.

    role: free-text role string (e.g. "Junior Backend Engineer"). When
    `difficulty` is not explicitly pinned by the caller, this is used to skew
    the pick's difficulty mix — more easy for junior roles, more medium/hard
    for senior roles — via infer_seniority()/_weighted_choice() instead of a
    flat random.choice.

    jd_seniority: an AI-derived seniority signal from the job description
    (see services.question_generator.analyze_job_description) — takes
    precedence over infer_seniority(role) when present, since it reflects
    the actual role requirements rather than a keyword match on the role
    title string.

    jd_topics: AI-derived topics/keywords from the job description — biases
    (not filters) the pick toward questions whose topic matches, via
    _weighted_choice's JD boost.

    exclude_ids: question ids to skip — e.g. ones already assigned earlier in
    the same session (see "Next question" in routers/interview.py), so asking
    for another problem doesn't risk re-serving the one just finished.
    """
    explicit_difficulty = difficulty is not None
    seniority = jd_seniority or infer_seniority(role)
    if difficulty is None:
        difficulty = ["easy", "medium", "hard"] if seniority == "senior" else ["easy", "medium"]
    elif isinstance(difficulty, str):
        difficulty = [difficulty]

    candidates = [
        q for q in _all_questions()
        if q.get("track") == track and language in (q.get("languages") or [])
        and (topic is None or q.get("topic") == topic)
        and (q.get("difficulty") or "medium") in difficulty
        and q["id"] not in (exclude_ids or set())
    ]
    if not candidates:
        return None
    if explicit_difficulty:
        return random.choice(candidates)
    return _weighted_choice(candidates, seniority, jd_topics)


def get_question(question_id: str) -> dict | None:
    return next((q for q in _all_questions() if q.get("id") == question_id), None)


def pick_behavioral_question(
    topic: str | None = None,
    difficulty: str | list[str] | None = None,
    role: str | None = None,
    jd_seniority: str | None = None,
    jd_topics: list[str] | None = None,
) -> dict | None:
    """Random behavioral question, optionally filtered by topic and difficulty.

    role/jd_seniority/jd_topics: see pick_question — jd_seniority takes
    precedence over role-based inference when present."""
    explicit_difficulty = difficulty is not None
    if isinstance(difficulty, str):
        difficulty = [difficulty]
    candidates = [
        q for q in _all_questions()
        if q.get("track") == "behavioral"
        and (topic is None or q.get("topic") == topic)
        and (difficulty is None or (q.get("difficulty") or "medium") in difficulty)
    ]
    if not candidates:
        return None
    if explicit_difficulty:
        return random.choice(candidates)
    return _weighted_choice(candidates, jd_seniority or infer_seniority(role), jd_topics)


def pick_system_design_question(
    difficulty: str | list[str] | None = None,
    role: str | None = None,
    jd_seniority: str | None = None,
    jd_topics: list[str] | None = None,
    exclude_ids: set[str] | None = None,
) -> dict | None:
    """Random system-design question. Includes all difficulties by default (unlike
    pick_question which excludes hard). None if the bank has no SD questions yet.

    role/jd_seniority/jd_topics: see pick_question — jd_seniority takes
    precedence over role-based inference when present.

    exclude_ids: question ids to skip — e.g. ones already assigned earlier in
    the same session, so asking for another problem doesn't re-serve the one
    just finished."""
    explicit_difficulty = difficulty is not None
    if isinstance(difficulty, str):
        difficulty = [difficulty]
    candidates = [
        q for q in _all_questions()
        if q.get("track") == "system-design"
        and (difficulty is None or (q.get("difficulty") or "medium") in difficulty)
        and q["id"] not in (exclude_ids or set())
    ]
    if not candidates:
        return None
    if explicit_difficulty:
        return random.choice(candidates)
    return _weighted_choice(candidates, jd_seniority or infer_seniority(role), jd_topics)

