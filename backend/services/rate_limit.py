"""
Rate limiter — sliding window, Postgres-backed.

Every request inserts one row into rate_limit_events. The check counts rows
in the trailing 60 seconds for the requesting user. Both backend replicas
query the same Postgres instance, so the limit is truly per-user across the
fleet (unlike the previous in-memory deque which gave each replica its own
independent counter).

Old rows (> 5 minutes) are pruned on each check to prevent unbounded growth.
No separate cron job is needed — the table stays small because only the
trailing window matters.

Fallback: if Supabase is not configured (local dev without a DB), the limiter
falls back to the previous in-memory deque so development still works without
credentials.
"""

from __future__ import annotations

import os
import time
from collections import defaultdict, deque
from threading import Lock

from fastapi import HTTPException, status

from services.logger import log

_WINDOW_SECONDS = 60
_PRUNE_AFTER_SECONDS = 300

# ── Groq account-wide budget ──────────────────────────────────────────────────
# Groq's own per-account rate limit (confirmed live against a 429 response
# body: "Limit 30, Used 30" requests per minute) is shared across every call
# this backend makes to it — the interviewer conversation (llm.py) AND the
# guardrail's LLM judges (guardrail.py) all draw from the same 30 RPM pool,
# across every replica. A 50-concurrent-user load test showed the problem
# directly: each request tried Groq first regardless, so a large share of
# attempts round-tripped to Groq just to get a 429 before falling back —
# wasted latency under exactly the load where latency matters most.
#
# GROQ_RPM_BUDGET is set safely under the real 30 RPM ceiling (not AT it) so
# this backend's own bookkeeping lands the account under its limit even
# accounting for the small read-then-write race in _check_postgres below
# (harmless here — worst case a couple of extra calls slip through in a
# given minute, not a correctness issue for a soft protective throttle).
GROQ_RPM_BUDGET = int(os.environ.get("GROQ_RPM_BUDGET", "24"))
_GROQ_GLOBAL_KEY = "__groq_global_budget__"


def groq_budget_available() -> bool:
    """True if the shared Groq account still has budget this minute.
    Callers should skip straight to their fallback path (Ollama in llm.py,
    fail-open False in guardrail.py) on a False return, instead of making a
    Groq call that's very likely to just 429. Uses the same cross-replica
    Postgres-backed counter as check_rate_limit, keyed globally instead of
    per-user. Fails open (True) if the check itself errors — a real 429 from
    Groq remains the ultimate safety net either way."""
    try:
        check_rate_limit(_GROQ_GLOBAL_KEY, max_per_minute=GROQ_RPM_BUDGET)
        return True
    except HTTPException:
        return False
    except Exception as exc:
        log.error("rate_limit.groq_budget_check_failed", error=str(exc))
        return True


def check_rate_limit(key: str, max_per_minute: int = 30) -> None:
    """Raises HTTP 429 if `key` has exceeded max_per_minute requests in the
    trailing 60 seconds. Uses Postgres when available, falls back to an
    in-memory deque for local dev without a configured database."""
    from services.supabase_client import get_supabase  # local import avoids circular dep

    sb = get_supabase()
    if sb:
        try:
            _check_postgres(sb, key, max_per_minute)
        except HTTPException:
            raise
        except Exception as exc:
            log.error("rate_limit.postgres_check_failed", error=str(exc))
            _check_memory(key, max_per_minute)
    else:
        _check_memory(key, max_per_minute)


# ── Postgres implementation ───────────────────────────────────────────────────

def _check_postgres(sb, key: str, max_per_minute: int) -> None:
    from datetime import datetime, timedelta, timezone

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=_WINDOW_SECONDS)
    prune_before = now - timedelta(seconds=_PRUNE_AFTER_SECONDS)

    # Count requests in the trailing window
    result = (
        sb.table("rate_limit_events")
        .select("id", count="exact")
        .eq("user_id", key)
        .gte("ts", window_start.isoformat())
        .execute()
    )
    count = result.count or 0

    if count >= max_per_minute:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many requests — please slow down and try again shortly.",
        )

    # Record this request
    sb.table("rate_limit_events").insert({"user_id": key, "ts": now.isoformat()}).execute()

    # Prune old rows (fire-and-forget; failure is acceptable)
    try:
        sb.table("rate_limit_events").delete().lt("ts", prune_before.isoformat()).execute()
    except Exception:
        pass


# ── In-memory fallback (local dev only) ──────────────────────────────────────

_buckets: dict[str, deque] = defaultdict(deque)
_lock = Lock()


def _check_memory(key: str, max_per_minute: int) -> None:
    now = time.monotonic()
    with _lock:
        bucket = _buckets[key]
        while bucket and now - bucket[0] > _WINDOW_SECONDS:
            bucket.popleft()
        if len(bucket) >= max_per_minute:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests — please slow down and try again shortly.",
            )
        bucket.append(now)
