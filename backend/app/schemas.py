from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class ChatRequest(BaseModel):
    message: str
    chat_id: str | None = None
    project_id: str | None = None
    model: str | None = None
    stream: bool = True
    reasoning_depth: Literal["auto", "quick", "standard", "deep"] = "auto"
    request_id: UUID | None = None
    user_message_id: UUID | None = None
    assistant_message_id: UUID | None = None
    reuse_user_message_id: UUID | None = None


class ChatUpdate(BaseModel):
    title: str | None = None
    project_id: str | None = None


class Citation(BaseModel):
    title: str
    author: str | None = None
    source_type: str
    reference: str | None = None
    reliability_level: str
    snippet: str
    score: float | None = None


class DocumentMetadata(BaseModel):
    title: str
    author: str | None = None
    source_type: str = "Other"
    madhab: str = "Unknown"
    period: str = "Unknown"
    geography: str | None = None
    language: str = "English"
    reference: str | None = None
    reliability_level: str = "Unknown"
    copyright_status: str | None = "Public domain / sample"
    uploaded_by: str | None = "admin"


class EvalQuestionIn(BaseModel):
    question: str
    ideal_answer: str | None = None
    source_expectation: str | None = None
    category: str = "General"


class EvalRunIn(BaseModel):
    eval_question_id: str


class SettingsIn(BaseModel):
    key: str
    value: dict[str, Any]


class ProjectCreate(BaseModel):
    name: str
    description: str | None = None
    color: str = "emerald"
    chat_ids: list[str] = []


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    display_name: str | None = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str
