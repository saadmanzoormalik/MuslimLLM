from __future__ import annotations

import hmac
import os
from typing import Any

from fastapi import APIRouter, Header, HTTPException
from pydantic import BaseModel, Field

from .policy import classify_query_policy, validate_fabric_input
from .retrieval import build_retrieval_plan, evaluate_evidence
from .reviewers import deterministic_review_flags, required_reviewers
from .schemas import DraftClaim, EvidenceSource, FabricInput, QueryPolicy, RetrievalJob, VerificationResult
from .verification import release_gate, verify_claims_and_citations


router = APIRouter(prefix="/internal/fabric", tags=["Muslim Knowledge Fabric"])


def _authorize(x_fabric_key: str = Header(default="")) -> None:
    configured = os.getenv("FABRIC_INTERNAL_API_KEY", "")
    if not configured:
        raise HTTPException(status_code=503, detail="Fabric integration is not configured")
    if not hmac.compare_digest(x_fabric_key, configured):
        raise HTTPException(status_code=401, detail="Invalid fabric credential")


class PolicyRequest(BaseModel):
    query: str
    current_information_allowed: bool = True


class PlanRequest(BaseModel):
    policy: QueryPolicy
    specified_madhab: str | None = None


class EvidenceRequest(BaseModel):
    policy: QueryPolicy
    retrieval_jobs: list[RetrievalJob]
    sources: list[EvidenceSource] = Field(default_factory=list)
    conflicts: list[str] = Field(default_factory=list)


class VerifyRequest(BaseModel):
    draft_answer: str
    claims: list[DraftClaim] = Field(default_factory=list)
    proposed_citations: list[str] = Field(default_factory=list)
    evidence: dict[str, Any]
    policy: QueryPolicy
    original_query: str
    prompt_injection_detected: bool = False


class ReleaseRequest(BaseModel):
    verification: VerificationResult
    revision_count: int = 0


class ReviewRequest(BaseModel):
    answer: str
    policy: QueryPolicy


@router.get("/health")
def fabric_health() -> dict[str, Any]:
    return {"ok": True, "configured": bool(os.getenv("FABRIC_INTERNAL_API_KEY")), "runtime": "deterministic-control-plane-v1"}


@router.post("/validate", dependencies=[])
def validate_input(payload: FabricInput, x_fabric_key: str = Header(default="")) -> dict[str, Any]:
    _authorize(x_fabric_key)
    return validate_fabric_input(payload).model_dump()


@router.post("/classify")
def classify(payload: PolicyRequest, x_fabric_key: str = Header(default="")) -> dict[str, Any]:
    _authorize(x_fabric_key)
    return classify_query_policy(payload.query, current_information_allowed=payload.current_information_allowed).model_dump()


@router.post("/retrieval-plan")
def retrieval_plan(payload: PlanRequest, x_fabric_key: str = Header(default="")) -> list[dict[str, Any]]:
    _authorize(x_fabric_key)
    return [job.model_dump() for job in build_retrieval_plan(payload.policy, specified_madhab=payload.specified_madhab)]


@router.post("/evidence")
def evidence(payload: EvidenceRequest, x_fabric_key: str = Header(default="")) -> dict[str, Any]:
    _authorize(x_fabric_key)
    return evaluate_evidence(payload.policy, payload.retrieval_jobs, payload.sources, conflicts=payload.conflicts).model_dump()


@router.post("/review")
def review(payload: ReviewRequest, x_fabric_key: str = Header(default="")) -> dict[str, Any]:
    _authorize(x_fabric_key)
    return deterministic_review_flags(payload.answer, payload.policy)


@router.post("/verify")
def verify(payload: VerifyRequest, x_fabric_key: str = Header(default="")) -> dict[str, Any]:
    _authorize(x_fabric_key)
    from .schemas import EvidencePack

    result = verify_claims_and_citations(
        draft_answer=payload.draft_answer,
        claims=payload.claims,
        proposed_citations=payload.proposed_citations,
        evidence=EvidencePack.model_validate(payload.evidence),
        policy=payload.policy,
        original_query=payload.original_query,
        prompt_injection_detected=payload.prompt_injection_detected,
    )
    return result.model_dump()


@router.post("/release")
def release(payload: ReleaseRequest, x_fabric_key: str = Header(default="")) -> dict[str, Any]:
    _authorize(x_fabric_key)
    return release_gate(payload.verification, revision_count=payload.revision_count).model_dump()


@router.post("/control-plan")
def control_plan(payload: FabricInput, x_fabric_key: str = Header(default="")) -> dict[str, Any]:
    _authorize(x_fabric_key)
    validated = validate_fabric_input(payload)
    if not validated.valid:
        return {"input": validated.model_dump(), "policy": None, "retrieval_jobs": [], "reviewers": []}
    policy = classify_query_policy(validated.clean_query, current_information_allowed=payload.current_information_allowed)
    jobs = build_retrieval_plan(policy)
    return {
        "input": validated.model_dump(),
        "policy": policy.model_dump(),
        "retrieval_jobs": [job.model_dump() for job in jobs],
        "reviewers": required_reviewers(policy),
    }
