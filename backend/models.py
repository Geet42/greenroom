from typing import Optional, List
from pydantic import BaseModel


class StartSessionRequest(BaseModel):
    track: str
    role: Optional[str] = "Software Engineer"
    user_id: Optional[str] = None


class StartSessionResponse(BaseModel):
    session_id: str
    track: str
    question: str


class MessageRequest(BaseModel):
    session_id: str
    message: str
    code: Optional[str] = None
    language: Optional[str] = None


class MessageResponse(BaseModel):
    question: str
    done: bool = False


class RunCodeRequest(BaseModel):
    language: str
    version: str
    source: str
    stdin: Optional[str] = ""


class EndSessionRequest(BaseModel):
    session_id: str


class EvaluationCategory(BaseModel):
    category: str
    score: int
    feedback: str


class EndSessionResponse(BaseModel):
    overall_score: int
    summary: str
    evaluations: List[EvaluationCategory]
