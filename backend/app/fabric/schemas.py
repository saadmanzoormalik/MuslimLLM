from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


RiskLevel = Literal["low", "medium", "high", "critical"]
Confidence = Literal["high", "medium", "low", "insufficient"]


class FabricInput(BaseModel):
    query: str
    conversation_context: str = ""
    user_language: str = "English"
    reasoning_depth: Literal["quick", "standard", "deep"] = "standard"
    current_information_allowed: bool = True
    scholar_mode: bool = False


class ValidatedInput(BaseModel):
    query_id: str
    original_query: str
    clean_query: str
    security_flags: list[str] = Field(default_factory=list)
    valid: bool
    rejection_reason: str | None = None


class QueryPolicy(BaseModel):
    categories: list[str]
    answer_mode: str
    values_sensitive: bool = False
    quran_required: bool = False
    hadith_required: bool = False
    fiqh_sensitive: bool = False
    madhab_sensitive: bool = False
    scientific_sources_required: bool = False
    historical_sources_required: bool = False
    current_sources_required: bool = False
    minimum_source_tier: int = 0
    minimum_source_count: int = 0
    source_diversity_required: bool = False
    citation_required: bool = False
    scholar_consultation_may_be_needed: bool = False
    risk_level: RiskLevel = "low"


class RetrievalJob(BaseModel):
    knowledge_base: str
    top_k: int
    metadata_filters: dict[str, Any] = Field(default_factory=dict)
    required_metadata: list[str] = Field(default_factory=list)
    minimum_authority_tier: int = 0
    required: bool = True
    live: bool = False


class EvidenceSource(BaseModel):
    source_id: str
    knowledge_base: str
    title: str
    snippet: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    authority_tier: int = 0
    score: float = 0
    quarantined: bool = False
    disabled: bool = False
    prompt_injection_detected: bool = False


class EvidencePack(BaseModel):
    sources: list[EvidenceSource] = Field(default_factory=list)
    coverage_score: float = 0
    conflicts: list[str] = Field(default_factory=list)
    evidence_confidence: Confidence = "insufficient"
    rejection_reasons: list[str] = Field(default_factory=list)


class DraftClaim(BaseModel):
    claim: str
    supporting_source_ids: list[str] = Field(default_factory=list)
    confidence: str = "low"
    factual: bool = True


class VerificationResult(BaseModel):
    passed: bool
    unsupported_claims: list[str] = Field(default_factory=list)
    citation_failures: list[str] = Field(default_factory=list)
    religious_source_failures: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    required_revisions: list[str] = Field(default_factory=list)


class ReleaseDecision(BaseModel):
    release: bool
    action: Literal["publish", "revise", "limited_answer"]
    verification_status: Literal["passed", "passed_with_caution", "insufficient"]
    reasons: list[str] = Field(default_factory=list)
