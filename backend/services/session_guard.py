"""
Session-level access controls:
  - ownership check (you can only access your own sessions)
  - concurrent session cap (max N active sessions per user)
  - idle timeout (sessions expire after M minutes of inactivity)
"""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException

from auth import AuthenticatedUser
from services.supabase_client import get_supabase

MAX_ACTIVE_SESSIONS = int(os.environ.get("MAX_ACTIVE_SESSIONS", "3"))
SESSION_IDLE_TIMEOUT_MINUTES = int(os.environ.get("SESSION_IDLE_TIMEOUT_MINUTES", "30"))
SESSION_MAX_DURATION_MINUTES = int(os.environ.get("SESSION_MAX_DURATION_MINUTES", "60"))


def check_ownership(session: dict, user: AuthenticatedUser) -> None:
    owner = session.get("user_id")
    if owner and owner != user.id:
        raise HTTPException(status_code=403, detail="You don't have access to this session")


def check_session_limit(user_id: str) -> None:
    """Rejects if the user already has MAX_ACTIVE_SESSIONS open sessions."""
    sb = get_supabase()
    if not sb:
        return
    resp = sb.table("sessions").select("id", count="exact").eq("user_id", user_id).eq("status", "active").execute()
    count = resp.count or 0
    if count >= MAX_ACTIVE_SESSIONS:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You already have {count} active session(s). "
                f"End an existing session before starting a new one."
            ),
        )


def _parse_ts(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            return None
    return value


def check_idle_timeout(session: dict) -> None:
    """Raises 410 if the session has been idle longer than SESSION_IDLE_TIMEOUT_MINUTES."""
    last_activity = _parse_ts(session.get("last_activity_at"))
    if not last_activity:
        return
    elapsed_minutes = (datetime.now(timezone.utc) - last_activity).total_seconds() / 60
    if elapsed_minutes > SESSION_IDLE_TIMEOUT_MINUTES:
        raise HTTPException(
            status_code=410,
            detail=(
                f"This session has been idle for over {SESSION_IDLE_TIMEOUT_MINUTES} minutes "
                f"and has expired. Start a new session to continue."
            ),
        )


def session_expires_at(session: dict) -> datetime | None:
    """Absolute wall-clock deadline for this session (created_at +
    SESSION_MAX_DURATION_MINUTES), or None if created_at is unknown. Exposed
    to the API responses (StartSessionResponse/ResumeSessionResponse) so the
    frontend can drive a countdown off server truth instead of a client-side
    timer started fresh on every page load/refresh."""
    created_at = _parse_ts(session.get("created_at"))
    if not created_at:
        return None
    return created_at + timedelta(minutes=SESSION_MAX_DURATION_MINUTES)


def check_session_duration(session: dict) -> None:
    """Raises 410 if the session has been open longer than
    SESSION_MAX_DURATION_MINUTES in absolute wall-clock time — independent of
    the idle timeout above, which only catches gaps between messages, not a
    candidate who keeps a session alive with steady activity indefinitely."""
    expires_at = session_expires_at(session)
    if not expires_at:
        return
    if datetime.now(timezone.utc) > expires_at:
        raise HTTPException(
            status_code=410,
            detail=(
                f"This session has been open for over {SESSION_MAX_DURATION_MINUTES} minutes "
                f"and has expired. Start a new session to continue."
            ),
        )
