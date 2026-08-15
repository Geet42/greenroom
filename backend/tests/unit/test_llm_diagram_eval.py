"""Covers evaluate_diagram's defense against a malformed LLM response.

Before this fix, evaluate_diagram returned the LLM's raw dict untouched —
a type mismatch (e.g. proximity_score as a string) or a proximity_label
that didn't exactly match one of the 3 literals models.DiagramEvaluation
requires would only crash later, unguarded, in routers/interview.py's
`EndSessionResponse(diagram_evaluation=...)` construction — 500ing the
entire /api/interview/end request for a system-design candidate who had
already gotten a valid overall score.
"""
from unittest.mock import MagicMock, patch

from models import DiagramEvaluation, EndSessionResponse
from services import llm


class _FakeBoundLLM:
    def __init__(self, chain):
        self._chain = chain

    def __or__(self, _parser):
        return self._chain


def _question():
    return {"title": "URL Shortener", "expected_components": ["load balancer", "cache", "database"]}


def _history():
    return [
        {"role": "interviewer", "content": "Design a URL shortener."},
        {"role": "candidate", "content": "[Architecture diagram]\nComponents: API server, Database"},
    ]


def test_evaluate_diagram_normalizes_a_mismatched_proximity_label():
    """The prompt asks for one of 3 exact label strings, but nothing stops
    the LLM from drifting (capitalization, wording) — the label is now
    derived from the score instead of trusted verbatim, so a mismatch can't
    reach the strict Literal type downstream at all."""
    chain = MagicMock()
    chain.invoke.return_value = {
        "components_found": ["database"],
        "components_missing": ["load balancer", "cache"],
        "proximity_score": 8,
        "proximity_label": "Strong design!",  # not one of the 3 exact literals
        "feedback": "Add a cache and load balancer.",
    }
    make_llm_result = MagicMock()
    make_llm_result.bind.return_value = _FakeBoundLLM(chain)

    with patch.object(llm, "_make_azure_llm", return_value=make_llm_result):
        result = llm.evaluate_diagram(_history(), _question(), diagram_elements=None)

    assert result["proximity_label"] == "strong"  # derived from score=8, not the LLM's raw string
    # Must not crash when built into the real API response model.
    resp = EndSessionResponse(overall_score=7, summary="ok", evaluations=[], diagram_evaluation=result)
    assert resp.diagram_evaluation.proximity_label == "strong"


def test_evaluate_diagram_falls_back_to_default_on_wrong_types():
    """proximity_score as a string is a type the Literal/int schema can't
    coerce — must degrade to the safe default, never raise out of
    evaluate_diagram itself."""
    chain = MagicMock()
    chain.invoke.return_value = {
        "components_found": ["database"],
        "components_missing": ["load balancer"],
        "proximity_score": "eight",  # wrong type
        "proximity_label": "strong",
        "feedback": "Looks solid.",
    }
    make_llm_result = MagicMock()
    make_llm_result.bind.return_value = _FakeBoundLLM(chain)

    with patch.object(llm, "_make_azure_llm", return_value=make_llm_result), \
         patch.object(llm, "_fallback_chat", side_effect=RuntimeError("fallback unconfigured")):
        result = llm.evaluate_diagram(_history(), _question(), diagram_elements=None)

    # Falls back to the safe default rather than propagating a ValidationError.
    assert result["proximity_score"] == 0
    assert result["proximity_label"] == "needs work"
    DiagramEvaluation(**result)  # still must validate cleanly


def test_evaluate_diagram_success_path_passes_through_validated():
    chain = MagicMock()
    chain.invoke.return_value = {
        "components_found": ["load balancer", "cache", "database"],
        "components_missing": [],
        "proximity_score": 9,
        "proximity_label": "reasonable",  # deliberately inconsistent with score — label is re-derived
        "feedback": "Great coverage.",
    }
    make_llm_result = MagicMock()
    make_llm_result.bind.return_value = _FakeBoundLLM(chain)

    with patch.object(llm, "_make_azure_llm", return_value=make_llm_result):
        result = llm.evaluate_diagram(_history(), _question(), diagram_elements=None)

    assert result["proximity_score"] == 9
    assert result["proximity_label"] == "strong"
    DiagramEvaluation(**result)
