"""Unit tests for the in-memory rate limiter."""
import time

import pytest
from fastapi import HTTPException

from services.rate_limit import _GROQ_GLOBAL_KEY, _buckets, check_rate_limit, groq_budget_available


def _clear(key: str):
    _buckets.pop(key, None)


def test_allows_requests_under_limit():
    _clear("user-a")
    for _ in range(5):
        check_rate_limit("user-a", max_per_minute=10)


def test_blocks_on_limit_exceeded():
    _clear("user-b")
    for _ in range(5):
        check_rate_limit("user-b", max_per_minute=5)
    with pytest.raises(HTTPException) as exc:
        check_rate_limit("user-b", max_per_minute=5)
    assert exc.value.status_code == 429


def test_window_slides():
    """Entries older than 60 s are evicted so a fresh request is allowed."""
    _clear("user-c")
    bucket = _buckets["user-c"]
    # Simulate 5 requests that happened 61 seconds ago
    old_ts = time.monotonic() - 61
    for _ in range(5):
        bucket.append(old_ts)
    # Should not raise — all old entries are outside the window
    check_rate_limit("user-c", max_per_minute=5)


def test_different_users_are_independent():
    _clear("user-x")
    _clear("user-y")
    for _ in range(5):
        check_rate_limit("user-x", max_per_minute=5)
    # user-y hasn't used any quota
    check_rate_limit("user-y", max_per_minute=5)


# ── groq_budget_available ────────────────────────────────────────────────────

def test_groq_budget_available_under_limit(monkeypatch):
    _clear(_GROQ_GLOBAL_KEY)
    monkeypatch.setattr("services.rate_limit.GROQ_RPM_BUDGET", 3)
    assert groq_budget_available() is True
    assert groq_budget_available() is True
    assert groq_budget_available() is True


def test_groq_budget_unavailable_once_exhausted(monkeypatch):
    _clear(_GROQ_GLOBAL_KEY)
    monkeypatch.setattr("services.rate_limit.GROQ_RPM_BUDGET", 2)
    assert groq_budget_available() is True
    assert groq_budget_available() is True
    # Third call this minute is over budget — should report unavailable
    # rather than raising, so callers can fall back cleanly.
    assert groq_budget_available() is False


def test_groq_budget_is_shared_globally_not_per_caller():
    """Unlike check_rate_limit's per-user keys, groq_budget_available has no
    caller-supplied key — every call site (llm.py's two, guardrail.py's two)
    draws from the same account-wide bucket, matching Groq's own limit being
    per-account rather than per-user."""
    _clear(_GROQ_GLOBAL_KEY)
    bucket = _buckets[_GROQ_GLOBAL_KEY]
    assert len(bucket) == 0
    groq_budget_available()
    assert len(bucket) == 1
    groq_budget_available()
    assert len(bucket) == 2
