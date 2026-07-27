"""Smoke tests: Pydantic models parse and reject correctly."""
import pytest
from pydantic import ValidationError

from models import AnalyticsEventRequest, MessageRequest, StartSessionRequest


def test_start_session_valid():
    r = StartSessionRequest(track="technical", role="Software Engineer")
    assert r.track == "technical"


def test_start_session_defaults():
    r = StartSessionRequest(track="behavioral")
    assert r.role == "Software Engineer"


def test_message_request_requires_session_and_message():
    with pytest.raises(ValidationError):
        MessageRequest()  # missing required fields


def test_analytics_event_valid():
    r = AnalyticsEventRequest(event="code_run", properties={"language": "python"})
    assert r.event == "code_run"


def test_analytics_event_no_properties():
    r = AnalyticsEventRequest(event="page_view")
    assert r.properties is None


def test_analytics_event_rejects_oversized_properties():
    with pytest.raises(ValidationError):
        AnalyticsEventRequest(event="code_run", properties={"blob": "x" * 3000})


def test_analytics_event_rejects_empty_event_name():
    with pytest.raises(ValidationError):
        AnalyticsEventRequest(event="")
