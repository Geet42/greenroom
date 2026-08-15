from contextlib import ExitStack
from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from auth import AuthenticatedUser, get_current_user
from routers import analytics
from services import metrics, persistence, rate_limit


@pytest.fixture(autouse=True)
def _isolated_state():
    with ExitStack() as stack:
        stack.enter_context(patch.object(persistence, "get_supabase", return_value=None))
        stack.enter_context(patch.object(analytics, "persist_analytics_event"))
        rate_limit._buckets.clear()
        yield


@pytest.fixture
def client():
    app = FastAPI()
    app.include_router(analytics.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: AuthenticatedUser(id="user-1")
    return TestClient(app)


def _page_view_count(path: str) -> float:
    return metrics.PAGE_VIEW_TOTAL.labels(path=path)._value.get()


def test_page_view_event_increments_known_path(client):
    before = _page_view_count("/dashboard")
    resp = client.post("/api/analytics/event", json={"event": "page_view", "properties": {"path": "/dashboard"}})
    assert resp.status_code == 202
    assert _page_view_count("/dashboard") == before + 1


def test_page_view_event_with_unknown_path_falls_back_to_other(client):
    before = _page_view_count("other")
    resp = client.post("/api/analytics/event", json={"event": "page_view", "properties": {"path": "/not-a-real-route"}})
    assert resp.status_code == 202
    assert _page_view_count("other") == before + 1


def test_non_page_view_event_does_not_touch_page_view_counter(client):
    before = _page_view_count("/dashboard")
    resp = client.post("/api/analytics/event", json={"event": "code_run", "properties": {"language": "python"}})
    assert resp.status_code == 202
    assert _page_view_count("/dashboard") == before
