"""Unit tests for question_bank.parse_function_name.

Covers the two function_name conventions in the bank: plain functions
(CodeContests-derived, e.g. "two_sum") and LeetCode-style class methods
encoded as "Solution().methodName" (needed verbatim by test_runner, which
executes tests["call"] as literal Python/JS — see parse_function_name's
docstring for why this isn't a data bug to "fix" at the source).
"""
from unittest.mock import patch

import pytest

from services.question_bank import (
    _topic_matches_jd,
    _weighted_choice,
    parse_function_name,
    pick_question,
)


def test_plain_function_name():
    assert parse_function_name("two_sum") == (None, "two_sum")


def test_class_method_function_name():
    assert parse_function_name("Solution().longestPalindromicSubsequence") == (
        "Solution", "longestPalindromicSubsequence",
    )


def test_class_method_with_different_class_name():
    assert parse_function_name("LRUCache().get") == ("LRUCache", "get")


@pytest.mark.parametrize("raw", [None, ""])
def test_empty_or_none_returns_empty_method(raw):
    assert parse_function_name(raw) == (None, "")


def test_malformed_looking_string_falls_back_to_raw():
    # No "()." separator — treated as a plain (if unusual) function name rather
    # than guessed apart, so callers still get *something* usable.
    assert parse_function_name("weird.name") == (None, "weird.name")


# --- _topic_matches_jd (AI-derived JD topics, not hardcoded keywords) -----

def test_topic_matches_jd_exact_and_substring():
    assert _topic_matches_jd("dynamic-programming", ["dynamic programming"]) is True
    assert _topic_matches_jd("caching", ["distributed caching layer"]) is True
    assert _topic_matches_jd("graph", ["graph algorithms"]) is True


def test_topic_matches_jd_no_match():
    assert _topic_matches_jd("strings", ["Kubernetes", "React"]) is False


def test_topic_matches_jd_handles_none_or_empty():
    assert _topic_matches_jd(None, ["React"]) is False
    assert _topic_matches_jd("arrays", None) is False
    assert _topic_matches_jd("arrays", []) is False


# --- _weighted_choice JD topic boost ---------------------------------------

def test_weighted_choice_boosts_jd_matching_topic():
    matching = {"id": "a", "difficulty": "medium", "topic": "caching"}
    non_matching = {"id": "b", "difficulty": "medium", "topic": "strings"}
    candidates = [matching, non_matching]

    picks = [_weighted_choice(candidates, "mid", jd_topics=["caching strategies"]) for _ in range(500)]
    matching_count = sum(1 for p in picks if p["id"] == "a")

    # Equal base weight (same difficulty), so without the boost this would be
    # ~50/50 — the JD-matching candidate should be picked meaningfully more
    # often than that.
    assert matching_count > 300  # comfortably above the ~250 a coin flip would give


def test_weighted_choice_no_jd_topics_is_unbiased_by_topic():
    a = {"id": "a", "difficulty": "medium", "topic": "caching"}
    b = {"id": "b", "difficulty": "medium", "topic": "strings"}
    picks = [_weighted_choice([a, b], "mid", jd_topics=None) for _ in range(500)]
    matching_count = sum(1 for p in picks if p["id"] == "a")
    # Roughly 50/50 without any JD signal — loose bounds to avoid flakiness.
    assert 150 < matching_count < 350


# --- pick_question jd_seniority override ------------------------------------

def test_pick_question_jd_seniority_overrides_role_for_difficulty_pool():
    hard_question = {
        "id": "hard-1", "track": "technical", "languages": ["python"],
        "topic": "graph", "difficulty": "hard",
    }
    with patch("services.question_bank._all_questions", return_value=[hard_question]):
        # role alone says "junior" -> hard is excluded, so this would return None.
        assert pick_question("technical", role="Junior Engineer") is None
        # jd_seniority="senior" overrides that and includes hard.
        result = pick_question("technical", role="Junior Engineer", jd_seniority="senior")
        assert result is not None
        assert result["id"] == "hard-1"
