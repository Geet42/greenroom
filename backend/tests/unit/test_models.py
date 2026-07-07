"""Smoke tests: Pydantic models parse and reject correctly."""
import pytest
from pydantic import ValidationError

from models import MessageRequest, RunCodeRequest, StartSessionRequest


def test_start_session_valid():
    r = StartSessionRequest(track="technical", role="Software Engineer")
    assert r.track == "technical"


def test_start_session_defaults():
    r = StartSessionRequest(track="behavioral")
    assert r.role == "Software Engineer"


def test_message_request_requires_session_and_message():
    with pytest.raises(ValidationError):
        MessageRequest()  # missing required fields


def test_run_code_request():
    r = RunCodeRequest(language="python", version="3.10.0", source="print('hi')")
    assert r.stdin == ""
