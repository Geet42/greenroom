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

# ── Provider account-wide budgets ─────────────────────────────────────────────
# Both Groq and Azure OpenAI have a hard, per-account/deployment rate limit
# shared across every call this backend makes to them — regardless of which
# code path (interviewer conversation, guardrail's LLM judges, evaluation,
# self-critique) triggered the call, and across every replica. A 50-
# concurrent-user load test showed both ceilings directly: Groq confirmed
# live via a 429 body ("Limit 30, Used 30" requests/minute); Azure OpenAI's
# real configured limit was read straight from the deployment itself
# (`az cognitiveservices account deployment show`): 100 requests/minute,
# 100,000 tokens/minute on the GlobalStandard SKU. Checking a budget before
# attempting a call — rather than discovering the limit via a 429 — avoids
# wasting latency on a request that's very likely to fail anyway, exactly
# when latency matters most.
#
# Each *_RPM_BUDGET is set safely under the provider's real ceiling (not AT
# it) so this backend's own bookkeeping lands the account under its limit
# even accounting for the small read-then-write race in _check_postgres
# below (harmless here — worst case a couple of extra calls slip through in
# a given minute, not a correctness issue for a soft protective throttle).
GROQ_RPM_BUDGET = int(os.environ.get("GROQ_RPM_BUDGET", "24"))
# Azure's 100 RPM is shared with evaluation + self-critique traffic too, not
# just the live-conversation fallback, so this leaves more headroom
# (proportionally) than Groq's budget does.
AZURE_RPM_BUDGET = int(os.environ.get("AZURE_RPM_BUDGET", "70"))

# rate_limit_events.user_id is a Postgres `uuid` column — a human-readable
# sentinel string here 22P02's ("invalid input syntax for type uuid") on
# every single check, silently degrading to the per-replica in-memory
# fallback instead of the intended cross-replica counter (each replica then
# enforces its own budget independently, letting the account-wide total run
# well past the provider's real limit under multiple replicas). These nil-
# like UUIDs are reserved and can never collide with a real user id.
_GROQ_GLOBAL_KEY = "00000000-0000-0000-0000-000000000000"
_AZURE_GLOBAL_KEY = "00000000-0000-0000-0000-000000000001"


def _provider_budget_available(key: str, max_per_minute: int, label: str) -> bool:
    """True if the shared provider account still has budget this minute.
    Callers should skip straight to their fallback path on a False return,
    instead of making a call very likely to just 429. Uses the same cross-
    replica Postgres-backed counter as check_rate_limit, keyed globally
    instead of per-user. Fails open (True) if the check itself errors — a
    real 429 from the provider remains the ultimate safety net either way."""
    try:
        check_rate_limit(key, max_per_minute=max_per_minute)
        return True
    except HTTPException:
        return False
    except Exception as exc:
        log.error(f"rate_limit.{label}_budget_check_failed", error=str(exc))
        return True


def groq_budget_available() -> bool:
    return _provider_budget_available(_GROQ_GLOBAL_KEY, GROQ_RPM_BUDGET, "groq")


def azure_budget_available() -> bool:
    return _provider_budget_available(_AZURE_GLOBAL_KEY, AZURE_RPM_BUDGET, "azure")


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
