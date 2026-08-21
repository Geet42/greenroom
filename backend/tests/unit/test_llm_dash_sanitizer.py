"""Unit tests for services.llm's em/en dash sanitizer — the candidate must
never see a typographic dash anywhere in generated text."""
from services.llm import (
    _ensure_eval_fields_nonempty,
    _ensure_nonempty,
    _strip_dashes_deep,
    _strip_typographic_dashes,
)

# ── _ensure_nonempty ─────────────────────────────────────────────────────────
# Guards a real production failure: the LLM call chain returned a genuinely
# empty string three times in one live session (confirmed via the transcript
# saved to Supabase), which sailed through every guardrail layer untouched
# since those only check for leaked content, not for emptiness.

def test_ensure_nonempty_passes_real_text_through_unchanged():
    assert _ensure_nonempty("A real question.", "fallback", "event") == "A real question."


def test_ensure_nonempty_substitutes_fallback_for_empty_string():
    assert _ensure_nonempty("", "fallback text", "event") == "fallback text"


def test_ensure_nonempty_substitutes_fallback_for_whitespace_only():
    assert _ensure_nonempty("   \n\t  ", "fallback text", "event") == "fallback text"


def test_ensure_nonempty_substitutes_fallback_for_none():
    assert _ensure_nonempty(None, "fallback text", "event") == "fallback text"


# ── _ensure_eval_fields_nonempty ─────────────────────────────────────────────
# Same failure class, for the evaluation report: EvaluationResult's text
# fields are plain `str` with no length constraint, so Pydantic accepts an
# empty string as "valid" — this would otherwise reach the Results page as a
# blank section with no error and no explanation.

def test_ensure_eval_fields_nonempty_fills_blank_summary():
    result = {
        "overall_score": 6, "summary": "  ",
        "star_analysis": {"situation": "ok", "task": "ok", "action": "ok", "result": "ok",
                           "star_score": 5, "missing_elements": []},
        "evaluations": [],
    }
    fixed = _ensure_eval_fields_nonempty(result)
    assert fixed["summary"].strip() != ""


def test_ensure_eval_fields_nonempty_fills_blank_star_fields():
    result = {
        "overall_score": 6, "summary": "Fine.",
        "star_analysis": {"situation": "", "task": "ok", "action": None, "result": "ok",
                           "star_score": 5, "missing_elements": []},
        "evaluations": [],
    }
    fixed = _ensure_eval_fields_nonempty(result)
    assert fixed["star_analysis"]["situation"] == "N/A"
    assert fixed["star_analysis"]["action"] == "N/A"
    assert fixed["star_analysis"]["task"] == "ok"


def test_ensure_eval_fields_nonempty_fills_blank_category_feedback():
    result = {
        "overall_score": 6, "summary": "Fine.",
        "star_analysis": {"situation": "ok", "task": "ok", "action": "ok", "result": "ok",
                           "star_score": 5, "missing_elements": []},
        "evaluations": [
            {"category": "Clarity", "score": 5, "feedback": ""},
            {"category": "Structure", "score": 7, "feedback": "Well organized."},
        ],
    }
    fixed = _ensure_eval_fields_nonempty(result)
    assert fixed["evaluations"][0]["feedback"].strip() != ""
    assert fixed["evaluations"][1]["feedback"] == "Well organized."


def test_ensure_eval_fields_nonempty_leaves_real_content_untouched():
    result = {
        "overall_score": 8, "summary": "Strong candidate.",
        "star_analysis": {"situation": "Clear.", "task": "Clear.", "action": "Clear.", "result": "Clear.",
                           "star_score": 8, "missing_elements": []},
        "evaluations": [{"category": "Clarity", "score": 8, "feedback": "Very clear."}],
    }
    fixed = _ensure_eval_fields_nonempty(dict(result))
    assert fixed == result


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
