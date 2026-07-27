"""Tests for GET /interview/sessions — the backend-owned session list that
replaces the frontend querying the `sessions` table directly via the
Supabase JS client.

Mounts only the interview router in a bare FastAPI app (not the full `main`
app, which loads real Supabase creds from .env at import time) and patches
get_supabase so no test can touch a real database.
"""
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import AuthenticatedUser, get_current_user
from routers import interview


def _client():
    app = FastAPI()
    app.include_router(interview.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="user-1")
    return TestClient(app)


def test_list_sessions_returns_empty_list_when_supabase_unconfigured():
    with patch.object(interview, "get_supabase", return_value=None):
        resp = _client().get("/api/interview/sessions")
    assert resp.status_code == 200
    assert resp.json() == []


def test_list_sessions_returns_rows_scoped_to_current_user():
    rows = [
        {"id": "s-1", "track": "behavioral", "role": "Backend Engineer",
         "overall_score": 8, "status": "completed", "created_at": "2026-07-01T00:00:00+00:00"},
    ]
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = rows
    with patch.object(interview, "get_supabase", return_value=sb):
        resp = _client().get("/api/interview/sessions")
    assert resp.status_code == 200
    assert resp.json() == rows
    sb.table.assert_called_once_with("sessions")
    sb.table.return_value.select.return_value.eq.assert_called_once_with("user_id", "user-1")


def test_list_sessions_applies_limit_and_offset_as_a_range():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = []
    with patch.object(interview, "get_supabase", return_value=sb):
        resp = _client().get("/api/interview/sessions?limit=10&offset=20")
    assert resp.status_code == 200
    range_call = sb.table.return_value.select.return_value.eq.return_value.order.return_value.range
    range_call.assert_called_once_with(20, 29)


def test_list_sessions_rejects_limit_above_cap():
    resp = _client().get("/api/interview/sessions?limit=500")
    assert resp.status_code == 422


def test_list_sessions_treats_none_data_as_empty_list():
    sb = MagicMock()
    sb.table.return_value.select.return_value.eq.return_value.order.return_value.range.return_value.execute.return_value.data = None
    with patch.object(interview, "get_supabase", return_value=sb):
        resp = _client().get("/api/interview/sessions")
    assert resp.status_code == 200
    assert resp.json() == []
