"""Smoke tests: Pydantic models parse and reject correctly."""
import pytest
from pydantic import ValidationError

from models import MessageRequest, StartSessionRequest


def test_start_session_valid():
    r = StartSessionRequest(track="technical", role="Software Engineer")
    assert r.track == "technical"


def test_start_session_defaults():
    r = StartSessionRequest(track="behavioral")
    assert r.role == "Software Engineer"


def test_message_request_requires_session_and_message():
    with pytest.raises(ValidationError):
        MessageRequest()  # missing required fields
