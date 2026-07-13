from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from models import AnalyticsEventRequest
from services import persistence


def test_analytics_event_request_requires_event():
    with pytest.raises(ValidationError):
        AnalyticsEventRequest()


def test_analytics_event_request_optional_fields_default_none():
    r = AnalyticsEventRequest(event="code_run")
    assert r.session_id is None
    assert r.properties is None


def test_persist_analytics_event_noop_when_supabase_unconfigured():
    with patch.object(persistence, "get_supabase", return_value=None):
        # Should not raise even though Supabase isn't configured.
        persistence.persist_analytics_event("user-1", "session-1", "code_run", {"language": "python"})


def test_persist_analytics_event_swallows_supabase_errors():
    sb = MagicMock()
    sb.table.return_value.insert.return_value.execute.side_effect = RuntimeError("boom")
    with patch.object(persistence, "get_supabase", return_value=sb):
        # Analytics failures must never propagate and break the caller.
        persistence.persist_analytics_event("user-1", None, "session_start", None)


def test_persist_analytics_event_writes_expected_row():
    sb = MagicMock()
    with patch.object(persistence, "get_supabase", return_value=sb):
        persistence.persist_analytics_event("user-1", "session-1", "code_run", {"language": "python"})
    sb.table.assert_called_once_with("analytics_events")
    inserted = sb.table.return_value.insert.call_args[0][0]
    assert inserted["user_id"] == "user-1"
    assert inserted["session_id"] == "session-1"
    assert inserted["event"] == "code_run"
    assert inserted["properties"] == {"language": "python"}
