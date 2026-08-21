"""
Covers the "generate a new problem" path in question_generator.py — this
used to always produce a stdin/stdout problem (candidate writes a full
program), which meant every LLM-generated question forced a blank editor
with no boilerplate, unlike the LeetCode-derived bank entries. It now
produces a function-call problem (LeetCode-style), matching the majority
shape of the bank, so boilerplate/signature generation works for these too.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from services import question_generator


def _piston_result(stdout: str, code: int = 0, stderr: str = "") -> dict:
    return {"run": {"stdout": stdout, "stderr": stderr, "code": code}}


@pytest.mark.asyncio
async def test_run_solution_returns_one_output_per_call():
    source = "def add(a, b):\n    return a + b\n"
    calls = ["add(1, 2)", "add(5, 5)"]
    stdout = "\n".join(json.dumps(repr(v)) for v in [3, 10])

    with patch("services.piston.run_code", new=AsyncMock(return_value=_piston_result(stdout))):
        result = await question_generator._run_solution(source, calls)

    assert result == ["3", "10"]


@pytest.mark.asyncio
async def test_run_solution_returns_none_on_crash():
    with patch("services.piston.run_code", new=AsyncMock(return_value=_piston_result("", code=1, stderr="boom"))):
        result = await question_generator._run_solution("def f(): pass", ["f()"])
    assert result is None


@pytest.mark.asyncio
async def test_run_solution_returns_none_on_line_count_mismatch():
    # Only one output line for two calls — a crash mid-way, or a call that
    # raised inside the try/except and printed something unparsable.
    stdout = json.dumps(repr(1))
    with patch("services.piston.run_code", new=AsyncMock(return_value=_piston_result(stdout))):
        result = await question_generator._run_solution("def f(): pass", ["f()", "f()"])
    assert result is None


@pytest.mark.asyncio
async def test_select_or_generate_produces_call_expected_tests_not_stdio():
    """The core regression test: a generated question's tests must be
    call/expected shaped (so is_stdio is False and boilerplate generation
    engages), never stdin/stdout shaped."""
    spec = {
        "action": "generate",
        "title": "Add Two Numbers",
        "topic": "math",
        "difficulty": "easy",
        "prompt": "Implement add(a, b) that returns a + b.",
        "function_name": "add",
        "solution_python": "def add(a, b):\n    return a + b\n",
        "calls": ["add(1, 2)", "add(-1, 1)", "add(0, 0)"],
        "claimed_outputs": ["3", "0", "0"],
    }
    outputs = ["3", "0", "0"]

    with patch("services.question_bank._all_questions", return_value=[
        {"id": "existing-1", "track": "technical", "topic": "arrays", "difficulty": "easy", "title": "Existing"},
    ]), \
         patch.object(question_generator, "_ask_llm", return_value=json.dumps(spec)), \
         patch.object(question_generator, "_run_solution", new=AsyncMock(return_value=outputs)):
        question = await question_generator.select_or_generate_question("Software Engineer", "I like math")

    assert question is not None
    assert question["function_name"] == "add"
    assert question["languages"] == ["python"]
    for test in question["tests"]:
        assert "call" in test and "expected" in test
        assert "stdin" not in test and "stdout" not in test
    assert question["tests"][0] == {"call": "add(1, 2)", "expected": "3"}


@pytest.mark.asyncio
async def test_select_or_generate_falls_back_to_bank_when_calls_missing():
    spec = {"action": "generate", "title": "X", "topic": "y", "difficulty": "easy", "prompt": "p",
            "function_name": "f", "solution_python": "def f(): pass", "calls": []}
    bank_question = {"id": "bank-1", "track": "technical", "topic": "arrays", "difficulty": "easy",
                      "title": "Bank Q", "tests": [{"call": "f()", "expected": "1"}]}

    with patch("services.question_bank._all_questions", return_value=[bank_question]), \
         patch.object(question_generator, "_ask_llm", return_value=json.dumps(spec)), \
         patch("services.question_bank.pick_question", return_value=bank_question) as mock_pick:
        question = await question_generator.select_or_generate_question("Software Engineer", "")

    mock_pick.assert_called_once()
    assert question == bank_question


@pytest.mark.asyncio
async def test_select_or_generate_falls_back_to_bank_when_title_is_empty():
    # Same failure class as the live-conversation empty-response bug
    # (services/llm.py's _ensure_nonempty): a present-but-blank title/prompt
    # from the LLM would otherwise build a question whose problem panel
    # silently renders empty.
    spec = {
        "action": "generate", "title": "  ", "topic": "y", "difficulty": "easy",
        "prompt": "Implement f(x) that returns x.", "function_name": "f",
        "solution_python": "def f(x): return x", "calls": ["f(1)", "f(2)", "f(3)"],
    }
    bank_question = {"id": "bank-1", "track": "technical", "topic": "arrays", "difficulty": "easy",
                      "title": "Bank Q", "tests": [{"call": "f()", "expected": "1"}]}

    with patch("services.question_bank._all_questions", return_value=[bank_question]), \
         patch.object(question_generator, "_ask_llm", return_value=json.dumps(spec)), \
         patch("services.question_bank.pick_question", return_value=bank_question) as mock_pick:
        question = await question_generator.select_or_generate_question("Software Engineer", "")

    mock_pick.assert_called_once()
    assert question == bank_question


@pytest.mark.asyncio
async def test_select_or_generate_falls_back_to_bank_when_prompt_is_empty():
    spec = {
        "action": "generate", "title": "Some Problem", "topic": "y", "difficulty": "easy",
        "prompt": "", "function_name": "f",
        "solution_python": "def f(x): return x", "calls": ["f(1)", "f(2)", "f(3)"],
    }
    bank_question = {"id": "bank-1", "track": "technical", "topic": "arrays", "difficulty": "easy",
                      "title": "Bank Q", "tests": [{"call": "f()", "expected": "1"}]}

    with patch("services.question_bank._all_questions", return_value=[bank_question]), \
         patch.object(question_generator, "_ask_llm", return_value=json.dumps(spec)), \
         patch("services.question_bank.pick_question", return_value=bank_question) as mock_pick:
        question = await question_generator.select_or_generate_question("Software Engineer", "")

    mock_pick.assert_called_once()
    assert question == bank_question


# --- analyze_job_description (replaces hardcoded JD keyword matching) ------

def test_analyze_job_description_empty_input_short_circuits():
    with patch.object(question_generator, "_ask_llm") as mock_ask:
        assert question_generator.analyze_job_description("") is None
        assert question_generator.analyze_job_description("   ") is None
    mock_ask.assert_not_called()


def test_analyze_job_description_parses_seniority_and_topics():
    raw = json.dumps({"seniority": "senior", "topics": ["distributed systems", "Kafka", "caching"]})
    with patch.object(question_generator, "_ask_llm", return_value=raw):
        result = question_generator.analyze_job_description("Senior backend engineer, Kafka, caching...")
    assert result == {"seniority": "senior", "topics": ["distributed systems", "Kafka", "caching"]}


def test_analyze_job_description_caps_topics_at_six_and_strips():
    raw = json.dumps({"seniority": "mid", "topics": [f" topic{i} " for i in range(10)]})
    with patch.object(question_generator, "_ask_llm", return_value=raw):
        result = question_generator.analyze_job_description("some jd")
    assert result["topics"] == [f"topic{i}" for i in range(6)]


def test_analyze_job_description_invalid_seniority_normalized_to_none():
    raw = json.dumps({"seniority": "expert-guru", "topics": ["React"]})
    with patch.object(question_generator, "_ask_llm", return_value=raw):
        result = question_generator.analyze_job_description("some jd")
    assert result == {"seniority": None, "topics": ["React"]}


def test_analyze_job_description_nothing_useful_returns_none():
    raw = json.dumps({"seniority": "not-a-real-value", "topics": []})
    with patch.object(question_generator, "_ask_llm", return_value=raw):
        result = question_generator.analyze_job_description("some jd")
    assert result is None


def test_analyze_job_description_malformed_json_returns_none():
    with patch.object(question_generator, "_ask_llm", return_value="not json"):
        assert question_generator.analyze_job_description("some jd") is None


def test_analyze_job_description_falls_back_on_primary_failure():
    raw = json.dumps({"seniority": "junior", "topics": ["arrays"]})
    with patch.object(question_generator, "_ask_llm", side_effect=RuntimeError("groq down")), \
         patch.object(question_generator, "_ask_llm_fallback", return_value=raw) as mock_fallback:
        result = question_generator.analyze_job_description("some jd")
    mock_fallback.assert_called_once()
    assert result == {"seniority": "junior", "topics": ["arrays"]}


def test_analyze_job_description_returns_none_when_both_providers_fail():
    with patch.object(question_generator, "_ask_llm", side_effect=RuntimeError("groq down")), \
         patch.object(question_generator, "_ask_llm_fallback", side_effect=RuntimeError("fallback down")):
        assert question_generator.analyze_job_description("some jd") is None


# --- _jd_context_block -------------------------------------------------------

def test_jd_context_block_empty_when_no_analysis():
    assert question_generator._jd_context_block(None) == ""
    assert question_generator._jd_context_block({"seniority": "senior", "topics": []}) == ""


def test_jd_context_block_includes_topics():
    block = question_generator._jd_context_block({"seniority": "senior", "topics": ["Kafka", "caching"]})
    assert "Kafka" in block
    assert "caching" in block
