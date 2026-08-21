"""Unit tests for the guardrail layer."""
from unittest.mock import patch

import pytest

from services.guardrail import _llm_judge, candidate_requests_new_problem, sanitize, violates

# ── violates ─────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "That runs in O(n log n) time.",
    "The time complexity is O(n).",
    "Your solution runs in linear time.",
    "The optimal time complexity would be O(1).",
    "Your solution is O(n^2).",
])
def test_technical_violations_detected(text):
    assert violates(text, "technical")


@pytest.mark.parametrize("text", [
    "What do you think the time complexity is?",
    "Can you walk me through your approach?",
    "How would you handle edge cases?",
])
def test_technical_clean_messages_pass(text):
    assert not violates(text, "technical")


@pytest.mark.parametrize("text", [
    "You should use Redis for caching here.",
    "I'd recommend Cassandra for this write pattern.",
    "The best architecture is to use a message queue.",
    "You'll need to use a CDN for static assets.",
])
def test_sysdesign_violations_detected(text):
    assert violates(text, "system-design")


@pytest.mark.parametrize("text", [
    "What caching strategy would you consider?",
    "How would you scale the write path?",
    "What are the trade-offs of that approach?",
])
def test_sysdesign_clean_messages_pass(text):
    assert not violates(text, "system-design")


def test_behavioral_track_never_blocks():
    assert not violates("The optimal answer is X.", "behavioral")


# ── sanitize ─────────────────────────────────────────────────────────────────

def test_sanitize_passes_clean_draft():
    result = sanitize("What is your approach?", "technical", regenerate_fn=lambda: "never called")
    assert result == "What is your approach?"


def test_sanitize_uses_regenerated_draft_when_clean():
    good = "How would you characterize the efficiency?"
    result = sanitize("That runs in O(n).", "technical", regenerate_fn=lambda: good)
    assert result == good


def test_sanitize_falls_back_when_regeneration_also_leaks():
    result = sanitize(
        "That runs in O(n).",
        "technical",
        regenerate_fn=lambda: "It's O(n log n) by the way.",
    )
    # Must return one of the pre-written fallback questions, never the leaked draft
    assert "O(" not in result
    assert len(result) > 10


def test_sanitize_falls_back_when_regeneration_raises():
    def bad_regen():
        raise RuntimeError("LLM unavailable")

    result = sanitize("That runs in O(n).", "technical", regenerate_fn=bad_regen)
    assert "O(" not in result


# ── LLM judge (Layer 3) ───────────────────────────────────────────────────────

def test_llm_judge_returns_false_when_no_api_key(monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert _llm_judge("Some text", "technical") is False


def test_llm_judge_fails_open_on_network_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("services.guardrail._HTTP_CLIENT.post", side_effect=Exception("connection refused")):
        assert _llm_judge("Some text", "technical") is False


def test_llm_judge_detects_leak_via_yes_response(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_response = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {"choices": [{"message": {"content": "YES"}}]},
    })()
    with patch("services.guardrail._HTTP_CLIENT.post", return_value=mock_response):
        assert _llm_judge("Some novel phrasing that means linear time", "technical") is True


def test_llm_judge_passes_clean_via_no_response(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_response = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {"choices": [{"message": {"content": "NO"}}]},
    })()
    with patch("services.guardrail._HTTP_CLIENT.post", return_value=mock_response):
        assert _llm_judge("What do you think the complexity is?", "technical") is False


def test_sanitize_triggers_regen_on_llm_judge_hit(monkeypatch):
    """LLM judge catches a leak that regex missed; sanitize should regen."""
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_yes = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {"choices": [{"message": {"content": "YES"}}]},
    })()
    mock_no = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {"choices": [{"message": {"content": "NO"}}]},
    })()
    call_count = {"n": 0}
    def fake_post(*args, **kwargs):
        call_count["n"] += 1
        return mock_yes if call_count["n"] == 1 else mock_no

    good = "What is the efficiency of your solution?"
    with patch("services.guardrail._HTTP_CLIENT.post", side_effect=fake_post):
        result = sanitize("This runs efficiently in linear time", "technical", regenerate_fn=lambda: good)
    assert result == good


# ── candidate_requests_new_problem ────────────────────────────────────────────

@pytest.mark.parametrize("text", [
    "Can I get the next question?",
    "Give me another problem please.",
    "Can we move on to a different question?",
    "Skip this question.",
    "Change this problem for me.",
    "Give me my next DSA question.",
    "Give me the next system design question please.",
    "Can I get a different system design problem?",
    "Give me another challenge.",
    "I'm done with this problem, what's next?",
])
def test_candidate_new_problem_regex_matches(text, monkeypatch):
    # No API key configured -> if regex misses, the LLM-judge layer fails
    # open to False, so a True result here can only come from the regex layer.
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert candidate_requests_new_problem(text) is True


@pytest.mark.parametrize("text", [
    "I think the time complexity of my solution is O(n).",
    "Let me walk through my approach to this problem.",
    "I'd use a hashmap here to speed things up.",
    "Can you clarify what the constraints are?",
])
def test_candidate_new_problem_clean_messages_pass(text, monkeypatch):
    monkeypatch.delenv("GROQ_API_KEY", raising=False)
    assert candidate_requests_new_problem(text) is False


def test_candidate_new_problem_hint_filter_skips_llm_call_when_no_signal_words():
    # A message with none of the hint words should never even attempt the
    # LLM judge call, regardless of API key / mocking.
    with patch("services.guardrail._HTTP_CLIENT.post") as mock_post:
        assert candidate_requests_new_problem("I would use a two-pointer approach here.") is False
        mock_post.assert_not_called()


def test_candidate_new_problem_llm_judge_catches_novel_phrasing(monkeypatch):
    # Regex misses this phrasing (no listed noun immediately after "next"),
    # but it contains the hint word "next" so the LLM judge fires.
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    mock_response = type("R", (), {
        "raise_for_status": lambda self: None,
        "json": lambda self: {"choices": [{"message": {"content": "YES"}}]},
    })()
    with patch("services.guardrail._HTTP_CLIENT.post", return_value=mock_response):
        assert candidate_requests_new_problem("I'd like to try something next, this one's not for me") is True


def test_candidate_new_problem_llm_judge_fails_open_on_error(monkeypatch):
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    with patch("services.guardrail._HTTP_CLIENT.post", side_effect=Exception("network error")):
        assert candidate_requests_new_problem("something next something") is False
