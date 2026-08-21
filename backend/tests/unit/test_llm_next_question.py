"""Unit tests for next_question()'s system-prompt construction.

Real bug this covers: the prompt telling the model to "present the
problem once the candidate has introduced themselves" was sent
UNCONDITIONALLY on every turn, including the 10th follow-up — nothing
distinguished "this is the first time" from "this has already happened
several turns ago." Confirmed via a real production transcript: the
interviewer re-asked a candidate's background and re-asked their
solution approach after they'd already answered both, because the
prompt kept telling it the intro/presentation "hadn't happened yet."

is_new_assignment exists specifically to distinguish these two cases,
but before this fix it was only used to gate a downstream guardrail
check — never to change the prompt text itself. These tests inspect
the actual system message the model receives (via a RunnableLambda
standing in for the real LLM, which is the standard way to capture
what flows through a LangChain LCEL pipe without a real API call) and
assert it change correctly with is_new_assignment.
"""
from unittest.mock import patch

from langchain_core.messages import AIMessage
from langchain_core.runnables import RunnableLambda

from services import llm


def _capture_system_message(monkeypatch) -> dict:
    """Patches llm._make_llm so next_question()'s LCEL chain runs against a
    RunnableLambda instead of a real Groq call — captures the system
    message actually sent and returns a fixed reply."""
    captured: dict = {}

    def _fake_llm_call(prompt_value):
        captured["system"] = prompt_value.to_messages()[0].content
        return AIMessage(content="Fake follow-up question.")

    monkeypatch.setattr(llm, "_make_llm", lambda **kwargs: RunnableLambda(_fake_llm_call))
    return captured


TECH_QUESTION = {
    "prompt": "Write a function valid_anagram(s, t) that returns True if t is an anagram of s.",
    "function_name": "valid_anagram",
    "tests": [{"input": "anagram, nagaram", "expected": "True"}],
}

BEHAVIORAL_QUESTION = {
    "prompt": "Tell me about a time you disagreed with a teammate.",
    "expected_elements": ["situation", "resolution"],
}

SYSTEM_DESIGN_QUESTION = {
    "prompt": "Design a URL shortener.",
}


def _history():
    return [
        {"role": "candidate", "content": "hi my name is vishwajit"},
        {"role": "interviewer", "content": "Nice to meet you! Here's the problem..."},
        {"role": "candidate", "content": "this is the solution I came\n\n[Candidate's submitted code]\n```\nfrom collections import Counter\ndef valid_anagram(s, t):\n    return Counter(s) == Counter(t)\n```"},
    ]


class TestTechnicalTrack:
    def test_first_presentation_says_present_it(self, monkeypatch):
        captured = _capture_system_message(monkeypatch)
        with patch.object(llm, "groq_budget_available", return_value=True):
            llm.next_question(
                "technical", "Software Engineer", _history(),
                assigned_question=TECH_QUESTION, is_new_assignment=True,
            )
        assert "present it" in captured["system"].lower()
        assert "once their" in captured["system"].lower()

    def test_followup_turn_does_not_say_present_it(self, monkeypatch):
        """The actual bug: this must NOT tell the model to present/introduce
        the problem again on a turn where it's already been presented."""
        captured = _capture_system_message(monkeypatch)
        with patch.object(llm, "groq_budget_available", return_value=True):
            llm.next_question(
                "technical", "Software Engineer", _history(),
                assigned_question=TECH_QUESTION, is_new_assignment=False,
            )
        system_lower = captured["system"].lower()
        # "re-present it" legitimately contains the substring "present it" —
        # check for the specific old buggy instruction, not that substring.
        assert "once their introduction is done" not in system_lower
        assert "already been given" in system_lower
        assert "do not re-present it" in system_lower

    def test_followup_turn_tells_model_not_to_reask_approach(self, monkeypatch):
        """Direct fix for the observed bug: a candidate who already
        submitted a correct solution shouldn't be re-asked how they'd
        approach it."""
        captured = _capture_system_message(monkeypatch)
        with patch.object(llm, "groq_budget_available", return_value=True):
            llm.next_question(
                "technical", "Software Engineer", _history(),
                assigned_question=TECH_QUESTION, is_new_assignment=False,
            )
        assert "already submitted a correct solution" in captured["system"].lower()


class TestBehavioralTrack:
    def test_first_presentation_says_present_naturally(self, monkeypatch):
        captured = _capture_system_message(monkeypatch)
        with patch.object(llm, "groq_budget_available", return_value=True):
            llm.next_question(
                "behavioral", "Software Engineer", _history(),
                assigned_question=BEHAVIORAL_QUESTION, is_new_assignment=True,
            )
        assert "present this question naturally" in captured["system"].lower()

    def test_followup_turn_does_not_reintroduce_question(self, monkeypatch):
        captured = _capture_system_message(monkeypatch)
        with patch.object(llm, "groq_budget_available", return_value=True):
            llm.next_question(
                "behavioral", "Software Engineer", _history(),
                assigned_question=BEHAVIORAL_QUESTION, is_new_assignment=False,
            )
        system_lower = captured["system"].lower()
        assert "present this question naturally" not in system_lower
        assert "already been asked" in system_lower
        assert "do not re-introduce" in system_lower


class TestSystemDesignTrack:
    def test_followup_turn_does_not_reintroduce_problem(self, monkeypatch):
        captured = _capture_system_message(monkeypatch)
        with patch.object(llm, "groq_budget_available", return_value=True):
            llm.next_question(
                "system-design", "Software Engineer", _history(),
                assigned_question=SYSTEM_DESIGN_QUESTION, is_new_assignment=False,
            )
        system_lower = captured["system"].lower()
        assert "already been given this problem" in system_lower
        assert "do not re-present it" in system_lower


class TestEmptyResponseGuard:
    """Real production failure, confirmed via a live session's transcript:
    the LLM call returned a genuinely empty string three times in one
    session (each one saved to the database as an empty message) — none of
    the guardrail layers catch this since they only check for LEAKED
    content, not for emptiness. next_question must never return "" or
    whitespace-only text to the candidate."""

    def test_empty_llm_response_is_replaced_with_a_safe_fallback(self, monkeypatch):
        monkeypatch.setattr(llm, "_make_llm", lambda **kwargs: RunnableLambda(lambda pv: AIMessage(content="")))
        with patch.object(llm, "groq_budget_available", return_value=True):
            result = llm.next_question(
                "technical", "Software Engineer", _history(),
                assigned_question=TECH_QUESTION, is_new_assignment=True,
            )
        assert result.strip() != ""
        assert "let's continue" in result.lower()

    def test_whitespace_only_llm_response_is_replaced_with_a_safe_fallback(self, monkeypatch):
        monkeypatch.setattr(llm, "_make_llm", lambda **kwargs: RunnableLambda(lambda pv: AIMessage(content="   \n  ")))
        with patch.object(llm, "groq_budget_available", return_value=True):
            result = llm.next_question(
                "behavioral", "Software Engineer", _history(),
                assigned_question=BEHAVIORAL_QUESTION, is_new_assignment=False,
            )
        assert result.strip() != ""
