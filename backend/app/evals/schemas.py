from typing import Any

from pydantic import BaseModel


class EvalRunRequest(BaseModel):
    model_id: str | None = None
    question_set_id: str | None = None
    suite_ids: list[str] = []
    run_name: str | None = None
    temperature: float = 0.2
    max_questions: int | None = None
    use_llm_judge: bool = False
    include_adversarial: bool = True


class RefreshExternalRequest(BaseModel):
    provider: str | None = None


class CompareRequest(BaseModel):
    run_id: str | None = None


class ScholarReviewRequest(BaseModel):
    status: str
    note: str | None = None


class EvalModelOut(BaseModel):
    id: str
    provider: str
    model_name: str
    display_name: str
    model_family: str | None = None
    is_local: bool
    api_base: str | None = None
    api_model_name: str | None = None
    is_active: bool


class AdapterScore(BaseModel):
    provider: str
    model_name: str
    display_name: str
    model_version_or_date: str | None = None
    benchmark: str
    benchmark_category: str | None = None
    score: float | None = None
    score_unit: str = "points"
    max_score: float = 100
    normalized_score_0_100: float | None = None
    source_type: str = "Manual source"
    source_url: str | None = None
    source_name: str | None = None
    published_at: str | None = None
    confidence_level: str = "low"
    notes: str | None = None
    manually_configured: bool = True
    raw_payload_json: dict[str, Any] = {}
