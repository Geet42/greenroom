"""
Formal completeness contract for `questions` rows (Supabase table / local JSON
seed) — the ONE thing this codebase never had. Every other module treats the
row as a loosely-shaped dict (`.get()` everywhere, duck-typed by
`"stdin" in tests[0]`), which is fine for serving a question that already
exists, but leaves no single place that says what "complete" means. This
module is that place: `classify_and_validate()` is the sole authority the
audit/repair scripts use to decide OK vs REPAIRABLE vs unrepairable.

Deliberately soft: models here validate shape/presence, not semantic
correctness (that's what sandbox verification — services.harness_generator,
scripts.harness_verify — is for). Nothing in this file ever raises out of
`classify_and_validate` — a malformed row becomes a list of issues, not a
crash, since a bad row two years old and already serving reheated candidates
should not take a service down.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError

from models import ScaleMetadataTag

MIN_CALL_EXPECTED_TESTS = 4
MIN_STDIO_TESTS = 3
EXPECTED_ELEMENTS_COUNT = 4

ALL_LANGUAGES = ("python", "node", "java", "cpp")


class QuestionValidationIssue(BaseModel):
    field: str
    severity: Literal["error", "warning"]
    message: str


class CallExpectedTest(BaseModel):
    call: str = Field(min_length=1)
    expected: Any


class StdioTest(BaseModel):
    stdin: str = ""
    stdout: str = ""


class TechnicalCallExpectedQuestion(BaseModel):
    id: str
    track: Literal["technical"]
    topic: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    title: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    function_name: str = Field(min_length=1)
    languages: list[str] = Field(min_length=1)
    tests: list[CallExpectedTest] = Field(min_length=MIN_CALL_EXPECTED_TESTS)
    constraints: list[str] | None = None
    examples: list[dict] | None = None
    # Supabase-only caches — optional on the model itself; per-language
    # completeness (verified-present / confirmed-unsupported / never-attempted)
    # is a derived judgment made by the audit script reading these dicts
    # directly, not something a single required/optional flag can express.
    harnesses: dict[str, Any] | None = None
    signatures: dict[str, Any] | None = None


class TechnicalStdioQuestion(BaseModel):
    id: str
    track: Literal["technical"]
    topic: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    title: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    function_name: None = None
    languages: list[str] = Field(min_length=1)
    tests: list[StdioTest] = Field(min_length=MIN_STDIO_TESTS)
    constraints: list[str] | None = None
    examples: list[dict] | None = None
    visible_count: int | None = None


class SystemDesignQuestion(BaseModel):
    id: str
    track: Literal["system-design"]
    topic: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    title: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    expected_components: list[str] = Field(min_length=1)   # used by the diagram evaluator (services.llm.evaluate_diagram)
    # Structured problem brief — compulsory per-question metadata (LeetCode-style
    # "requirements doc" instead of a bare prompt string). Presented to the
    # candidate/interviewer via services.llm's system-design prompt builder.
    functional_requirements: list[str] = Field(min_length=1)
    non_functional_requirements: list[str] = Field(min_length=1)
    scaling_constraints: list[str] = Field(min_length=1)
    out_of_scope: list[str] = Field(min_length=1)
    # Legacy fields — predate the structured brief above, kept optional
    # (not required going forward) since nothing currently reads them:
    # scale_metadata/constraints are not wired into the interviewer prompt or
    # any frontend view for system-design (only technical's QuestionContext
    # uses that shape). Not deleting existing data, just no longer required.
    constraints: list[str] | None = None
    scale_metadata: list[ScaleMetadataTag] | None = None


class BehavioralQuestion(BaseModel):
    id: str
    track: Literal["behavioral"]
    topic: str | None = None
    difficulty: Literal["easy", "medium", "hard"] | None = None
    title: str = Field(min_length=1)
    prompt: str = Field(min_length=1)
    expected_elements: list[str] = Field(min_length=EXPECTED_ELEMENTS_COUNT, max_length=EXPECTED_ELEMENTS_COUNT)


def _is_stdio(row: dict) -> bool:
    tests = row.get("tests") or []
    return bool(tests) and isinstance(tests[0], dict) and "stdin" in tests[0]


def classify_and_validate(row: dict) -> tuple[BaseModel | None, list[QuestionValidationIssue]]:
    """Picks the right model for `row` by track (+ test shape, for technical)
    and validates it. Returns (parsed_model, []) on success, or (None, issues)
    on failure — never raises, so callers can log/report without a try/except
    around every row."""
    track = row.get("track")
    qid = row.get("id", "<no id>")

    if track == "technical":
        model_cls = TechnicalStdioQuestion if _is_stdio(row) else TechnicalCallExpectedQuestion
    elif track == "system-design":
        model_cls = SystemDesignQuestion
    elif track == "behavioral":
        model_cls = BehavioralQuestion
    else:
        return None, [QuestionValidationIssue(
            field="track", severity="error",
            message=f"question {qid!r} has unrecognized track {track!r}",
        )]

    try:
        return model_cls.model_validate(row), []
    except ValidationError as exc:
        issues = [
            QuestionValidationIssue(
                field=".".join(str(p) for p in err["loc"]) or "<root>",
                severity="error",
                message=err["msg"],
            )
            for err in exc.errors()
        ]
        return None, issues
