import json
from unittest.mock import MagicMock, patch

from langchain_core.messages import AIMessage

from services import llm


def _draft():
    return {
        "overall_score": 5,
        "summary": "Draft summary.",
        "star_analysis": {
            "situation": "ok", "task": "ok", "action": "ok", "result": "ok",
            "star_score": 5, "missing_elements": [],
        },
        "evaluations": [{"category": "clarity", "score": 5, "feedback": "fine"}],
    }


class _FakeBoundLLM:
    """Stands in for `_make_azure_llm(...).bind(...)` — supports `.invoke()`
    directly, since _self_critique calls it and then pipes the raw response
    through the real JsonOutputParser itself (rather than a LangChain `|`
    chain), so it can read usage_metadata off the raw response first."""

    def __init__(self, response: AIMessage):
        self._response = response

    def invoke(self, _messages):
        return self._response


def test_self_critique_disabled_returns_draft_unchanged():
    draft = _draft()
    with patch.object(llm, "EVAL_SELF_CRITIQUE_ENABLED", False), \
         patch.object(llm, "_make_azure_llm") as make_llm:
        result = llm._self_critique("technical", "backend", "transcript", draft)
    make_llm.assert_not_called()
    assert result is draft


def test_self_critique_applies_reviewer_revision():
    draft = _draft()
    revised = {
        "overall_score": 3,
        "summary": "Revised summary.",
        "star_analysis": draft["star_analysis"],
        "evaluations": [{"category": "clarity", "score": 3, "feedback": "actually weak"}],
    }

    make_llm_result = MagicMock()
    make_llm_result.bind.return_value = _FakeBoundLLM(AIMessage(content=json.dumps(revised)))

    with patch.object(llm, "EVAL_SELF_CRITIQUE_ENABLED", True), \
         patch.object(llm, "_make_azure_llm", return_value=make_llm_result):
        result = llm._self_critique("technical", "backend", "transcript", draft)

    assert result["overall_score"] == 3
    assert result["summary"] == "Revised summary."


def test_self_critique_falls_back_to_draft_on_error():
    draft = _draft()
    with patch.object(llm, "EVAL_SELF_CRITIQUE_ENABLED", True), \
         patch.object(llm, "_make_azure_llm", side_effect=RuntimeError("no key")):
        result = llm._self_critique("technical", "backend", "transcript", draft)
    assert result == draft
