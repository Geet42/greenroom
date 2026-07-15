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
