"""Unit tests for session-level access controls: ownership, concurrent
session cap, idle timeout, and candidate turn limit."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from auth import AuthenticatedUser
from services import session_guard
from services.session_guard import (
    check_idle_timeout,
    check_ownership,
    check_session_limit,
    is_turn_limit_reached,
)


def _user(user_id="user-1"):
    return AuthenticatedUser(id=user_id)


# --- check_ownership ---------------------------------------------------

def test_check_ownership_allows_matching_owner():
    session = {"user_id": "user-1"}
    check_ownership(session, _user("user-1"))  # should not raise


def test_check_ownership_rejects_mismatched_owner():
    session = {"user_id": "user-1"}
    with pytest.raises(HTTPException) as exc:
        check_ownership(session, _user("user-2"))
    assert exc.value.status_code == 403


def test_check_ownership_allows_session_with_no_owner():
    # Sessions created before auth was wired up (or anonymous) have no
    # user_id — ownership can't be enforced against nothing, so allow it.
    session = {"user_id": None}
    check_ownership(session, _user("user-2"))  # should not raise


# --- check_session_limit ------------------------------------------------

def test_check_session_limit_noop_when_supabase_unconfigured():
    with patch.object(session_guard, "get_supabase", return_value=None):
        check_session_limit("user-1")  # should not raise


def test_check_session_limit_allows_under_cap():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.count = 2
    with patch.object(session_guard, "get_supabase", return_value=sb):
        check_session_limit("user-1")  # should not raise (default cap is 3)


def test_check_session_limit_blocks_at_cap():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.count = 3
    with patch.object(session_guard, "get_supabase", return_value=sb):
        with pytest.raises(HTTPException) as exc:
            check_session_limit("user-1")
    assert exc.value.status_code == 429


def test_check_session_limit_treats_none_count_as_zero():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.count = None
    with patch.object(session_guard, "get_supabase", return_value=sb):
        check_session_limit("user-1")  # should not raise


# --- is_turn_limit_reached ------------------------------------------------

def test_turn_limit_not_reached_under_max():
    session = {"history": [{"role": "candidate", "content": "hi"}] * 3}
    assert is_turn_limit_reached(session) is False


def test_turn_limit_reached_at_max():
    session = {"history": [{"role": "candidate", "content": "hi"}] * session_guard.MAX_CANDIDATE_TURNS}
    assert is_turn_limit_reached(session) is True


def test_turn_limit_only_counts_candidate_turns():
    history = (
        [{"role": "interviewer", "content": "q"}] * session_guard.MAX_CANDIDATE_TURNS
        + [{"role": "candidate", "content": "hi"}]
    )
    session = {"history": history}
    assert is_turn_limit_reached(session) is False


# --- check_idle_timeout ------------------------------------------------

def test_idle_timeout_noop_when_no_last_activity():
    check_idle_timeout({})  # should not raise


def test_idle_timeout_allows_recent_activity():
    session = {"last_activity_at": datetime.now(timezone.utc)}
    check_idle_timeout(session)  # should not raise


def test_idle_timeout_raises_after_expiry():
    stale = datetime.now(timezone.utc) - timedelta(minutes=session_guard.SESSION_IDLE_TIMEOUT_MINUTES + 1)
    session = {"last_activity_at": stale}
    with pytest.raises(HTTPException) as exc:
        check_idle_timeout(session)
    assert exc.value.status_code == 410


def test_idle_timeout_parses_iso_string_with_z_suffix():
    stale = datetime.now(timezone.utc) - timedelta(minutes=session_guard.SESSION_IDLE_TIMEOUT_MINUTES + 1)
    session = {"last_activity_at": stale.isoformat().replace("+00:00", "Z")}
    with pytest.raises(HTTPException):
        check_idle_timeout(session)


def test_idle_timeout_ignores_unparsable_string():
    session = {"last_activity_at": "not-a-date"}
    check_idle_timeout(session)  # should not raise
