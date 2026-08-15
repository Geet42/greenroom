from unittest.mock import MagicMock, patch

import pytest
from pydantic import ValidationError

from models import AnalyticsEventRequest
from routers.analytics import _merge_plural_dupes
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


# --- _merge_plural_dupes (dashboard topic-breakdown grouping) --------------

def test_merge_plural_dupes_merges_singular_and_plural_pair():
    topics = {
        "array": {"easy": 3, "medium": 2, "hard": 0},
        "arrays": {"easy": 1, "medium": 0, "hard": 0},
    }
    result = _merge_plural_dupes(topics)
    assert result == {"array": {"easy": 4, "medium": 2, "hard": 0}}


def test_merge_plural_dupes_leaves_plural_only_topics_untouched():
    """"two-pointers" has no singular counterpart in the bank — must not be
    rewritten to "two-pointer" just because it ends in "s"."""
    topics = {"two-pointers": {"easy": 0, "medium": 1, "hard": 0}}
    result = _merge_plural_dupes(topics)
    assert result == topics


def test_merge_plural_dupes_leaves_unrelated_topics_untouched():
    topics = {
        "greedy": {"easy": 1, "medium": 0, "hard": 0},
        "math": {"easy": 0, "medium": 1, "hard": 0},
    }
    result = _merge_plural_dupes(topics)
    assert result == topics
