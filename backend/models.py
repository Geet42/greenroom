import json
from typing import List, Literal, Optional

from pydantic import BaseModel, Field, field_validator


class StartSessionRequest(BaseModel):
    track: Literal["behavioral", "technical", "system-design"]
    role: str = Field(default="Software Engineer", min_length=1, max_length=100)
    user_id: Optional[str] = None
    job_description: Optional[str] = Field(default=None, max_length=5000)
    # Optional, candidate-chosen — takes precedence over both the job
    # description's AI-inferred seniority and role-string keyword matching
    # (see jd_analysis merge in routers/interview.py:start_session).
    seniority: Optional[Literal["junior", "mid", "senior"]] = None


class VisibleTestResult(BaseModel):
    id: int
    label: str
    input: str
    expected: str
    output: Optional[str] = None
    error: Optional[str] = None
    passed: bool


class HiddenTestResult(BaseModel):
    id: int
    passed: bool


class RunTestsRequest(BaseModel):
    session_id: str
    language: str = Field(min_length=1, max_length=50)
    version: str = Field(min_length=1, max_length=50)
    source: str = Field(min_length=1, max_length=100_000)


class RunTestsResponse(BaseModel):
    status: str
    visible_tests: List[VisibleTestResult]
    hidden_tests: List[HiddenTestResult]
    passed: int
    total: int
    compile_error: Optional[str] = None
    error_type: Optional[Literal["transient", "permanent"]] = None


class StartSessionResponse(BaseModel):
    session_id: str
    track: str
    question: str
    expires_at: Optional[str] = None


class SessionSummary(BaseModel):
    id: str
    track: str
    role: Optional[str] = None
    overall_score: Optional[int] = None
    status: str
    created_at: str


class MessageRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=20_000)
    code: Optional[str] = Field(default=None, max_length=100_000)
    language: Optional[str] = Field(default=None, max_length=50)


class ScaleMetadataTag(BaseModel):
    """One structured scale/metadata tag for a system-design question, e.g.
    {"label": "Writes/day", "value": "100M (~1,200/sec)"} — a flexible
    label/value pair rather than fixed numeric columns, since different
    system-design problems care about very different metrics."""
    label: str
    value: str


class QuestionContext(BaseModel):
    """Sent to the frontend once per session, when the coding problem is first assigned."""
    id: str
    title: str
    difficulty: str
    prompt: str
    constraints: List[str]
    examples: List[dict]
    is_stdio: bool
    scale_metadata: List[ScaleMetadataTag] = []


class MessageResponse(BaseModel):
    question: str
    question_context: Optional[QuestionContext] = None


class BoilerplateResponse(BaseModel):
    boilerplate: Optional[str] = None
    supported: bool = True


class HistoryMessage(BaseModel):
    role: str
    content: str


class ResumeSessionResponse(BaseModel):
    session_id: str
    track: str
    history: List[HistoryMessage]
    question_context: Optional[QuestionContext] = None
    diagram_elements: List[dict] = []
    expires_at: Optional[str] = None


class SaveDiagramRequest(BaseModel):
    session_id: str
    elements: List[dict] = Field(default_factory=list, max_length=5000)


class EndSessionRequest(BaseModel):
    session_id: str


class EvaluationCategory(BaseModel):
    category: str
    score: int
    feedback: str


class STARAnalysis(BaseModel):
    situation: str
    task: str
    action: str
    result: str
    star_score: int
    missing_elements: List[str]


class DiagramEvaluation(BaseModel):
    components_found: List[str]
    components_missing: List[str]
    proximity_score: int = Field(ge=0, le=10)
    proximity_label: Literal["needs work", "reasonable", "strong"]
    feedback: str


class EndSessionResponse(BaseModel):
    overall_score: int
    summary: str
    star_analysis: Optional[STARAnalysis] = None
    evaluations: List[EvaluationCategory]
    diagram_evaluation: Optional[DiagramEvaluation] = None


class AnalyticsEventRequest(BaseModel):
    event: str = Field(min_length=1, max_length=100)
    session_id: Optional[str] = None
    properties: Optional[dict] = None

    @field_validator("properties")
    @classmethod
    def _bound_properties_size(cls, v: Optional[dict]) -> Optional[dict]:
        if v is not None and len(json.dumps(v)) > 2000:
            raise ValueError("properties payload too large (max 2000 bytes serialized)")
        return v
