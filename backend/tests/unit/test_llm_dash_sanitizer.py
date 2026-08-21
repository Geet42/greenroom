"""Unit tests for services.llm's em/en dash sanitizer — the candidate must
never see a typographic dash anywhere in generated text."""
from services.llm import _strip_dashes_deep, _strip_typographic_dashes


def test_strip_em_dash_clause_separator_becomes_comma():
    assert _strip_typographic_dashes("I led the project — and it shipped on time.") == \
        "I led the project, and it shipped on time."


def test_strip_en_dash_clause_separator_becomes_comma():
    assert _strip_typographic_dashes("Good design – bad execution.") == "Good design, bad execution."


def test_strip_numeric_range_dash_becomes_hyphen():
    assert _strip_typographic_dashes("Supports 10–20 requests per second.") == \
        "Supports 10-20 requests per second."
    assert _strip_typographic_dashes("Founded in 2013—2015.") == "Founded in 2013-2015."


def test_strip_dashes_leaves_clean_text_untouched():
    text = "This is a perfectly normal sentence with no dashes at all."
    assert _strip_typographic_dashes(text) == text


def test_strip_dashes_handles_none_and_empty():
    assert _strip_typographic_dashes(None) is None
    assert _strip_typographic_dashes("") == ""


def test_strip_dashes_deep_walks_nested_structure():
    payload = {
        "summary": "Strong candidate — clear communicator.",
        "evaluations": [
            {"category": "Clarity", "feedback": "Answers were direct — no rambling."},
            {"category": "Structure", "feedback": "Good STAR structure."},
        ],
        "star_analysis": {
            "missing_elements": ["result — not clearly stated"],
        },
        "overall_score": 7,
    }
    result = _strip_dashes_deep(payload)
    assert result["summary"] == "Strong candidate, clear communicator."
    assert result["evaluations"][0]["feedback"] == "Answers were direct, no rambling."
    assert result["evaluations"][1]["feedback"] == "Good STAR structure."
    assert result["star_analysis"]["missing_elements"] == ["result, not clearly stated"]
    assert result["overall_score"] == 7  # non-strings pass through untouched
