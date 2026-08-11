"""Unit tests for session-level access controls: ownership, concurrent
session cap, idle timeout, and absolute session duration cap."""
from datetime import datetime, timedelta, timezone
from unittest.mock import MagicMock, patch

import pytest
from fastapi import HTTPException

from auth import AuthenticatedUser
from services import session_guard
from services.session_guard import (
    check_idle_timeout,
    check_ownership,
    check_session_duration,
    check_session_limit,
    session_expires_at,
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


# --- session_expires_at / check_session_duration ------------------------

def test_session_expires_at_none_when_no_created_at():
    assert session_expires_at({}) is None


def test_session_expires_at_offset_from_created_at():
    created = datetime.now(timezone.utc)
    session = {"created_at": created}
    expires = session_expires_at(session)
    assert expires == created + timedelta(minutes=session_guard.SESSION_MAX_DURATION_MINUTES)


def test_session_expires_at_parses_iso_string():
    created = datetime.now(timezone.utc) - timedelta(minutes=5)
    session = {"created_at": created.isoformat()}
    expires = session_expires_at(session)
    assert expires is not None


def test_check_session_duration_noop_when_no_created_at():
    check_session_duration({})  # should not raise


def test_check_session_duration_allows_recent_session():
    session = {"created_at": datetime.now(timezone.utc)}
    check_session_duration(session)  # should not raise


def test_check_session_duration_raises_after_expiry():
    stale = datetime.now(timezone.utc) - timedelta(minutes=session_guard.SESSION_MAX_DURATION_MINUTES + 1)
    session = {"created_at": stale}
    with pytest.raises(HTTPException) as exc:
        check_session_duration(session)
    assert exc.value.status_code == 410


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
