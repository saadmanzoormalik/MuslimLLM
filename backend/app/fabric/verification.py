from __future__ import annotations

import re

from .schemas import DraftClaim, EvidencePack, QueryPolicy, ReleaseDecision, VerificationResult


BINDING_FATWA_PATTERNS = (
    r"\bI (?:hereby )?(?:issue|give|declare) (?:a )?(?:binding )?fatwa\b",
    r"\bthis is a binding religious ruling\b",
    r"\byou are religiously required to follow my ruling\b",
)
FALSE_CONSENSUS_PATTERNS = (
    r"\bthere is (?:complete|unanimous) consensus\b",
    r"\ball (?:muslims|scholars|madhabs) agree\b",
    r"\bislam (?:always|universally|unanimously) says\b",
)


def verify_claims_and_citations(
    *,
    draft_answer: str,
    claims: list[DraftClaim],
    proposed_citations: list[str],
    evidence: EvidencePack,
    policy: QueryPolicy,
    original_query: str,
    prompt_injection_detected: bool = False,
) -> VerificationResult:
    source_map = {source.source_id: source for source in evidence.sources}
    unsupported: list[str] = []
    citation_failures: list[str] = []
    religious_failures: list[str] = []
    revisions: list[str] = []

    for citation in proposed_citations:
        if citation not in source_map:
            citation_failures.append(f"unknown_source_id:{citation}")

    for claim in claims:
        missing = [source_id for source_id in claim.supporting_source_ids if source_id not in source_map]
        if missing:
            citation_failures.append(f"claim_references_unknown_source:{claim.claim}")
        if claim.factual and policy.citation_required and not claim.supporting_source_ids:
            unsupported.append(claim.claim)
        if claim.factual and claim.supporting_source_ids and all(source_id not in source_map for source_id in claim.supporting_source_ids):
            unsupported.append(claim.claim)

    for source_id in set(proposed_citations) & set(source_map):
        source = source_map[source_id]
        if source.knowledge_base == "QURAN_VERIFIED":
            if not source.metadata.get("surah") or not source.metadata.get("ayah"):
                religious_failures.append(f"quran_reference_incomplete:{source_id}")
        if source.knowledge_base == "HADITH_VERIFIED":
            if not source.metadata.get("collection") or not source.metadata.get("hadith_number"):
                religious_failures.append(f"hadith_reference_incomplete:{source_id}")

    if policy.minimum_source_count and len(evidence.sources) < policy.minimum_source_count:
        unsupported.append("minimum_source_count_not_met")
    if policy.scientific_sources_required and not any(source.knowledge_base == "GENERAL_SCIENCE_AND_ACADEMIC" for source in evidence.sources):
        unsupported.append("required_scientific_evidence_missing")
    if policy.current_sources_required and not any(source.knowledge_base == "LIVE_RESEARCH_CANDIDATES" for source in evidence.sources):
        unsupported.append("required_current_evidence_missing")
    if evidence.evidence_confidence == "insufficient" and policy.minimum_source_count:
        unsupported.append("evidence_sufficiency_gate_failed")
    if prompt_injection_detected:
        revisions.append("remove_any_prompt_injection_influence")
    if original_query.strip() and original_query.strip() == draft_answer.strip():
        revisions.append("user_prompt_mixed_into_answer")
    if any(re.search(pattern, draft_answer, re.I) for pattern in BINDING_FATWA_PATTERNS):
        revisions.append("binding_fatwa_language")
    if any(re.search(pattern, draft_answer, re.I) for pattern in FALSE_CONSENSUS_PATTERNS):
        revisions.append("unsupported_consensus_language")
    if not draft_answer.strip():
        revisions.append("empty_answer")

    contradictions = list(evidence.conflicts)
    if contradictions:
        revisions.append("surface_material_contradictions")
    for item in unsupported:
        revisions.append(f"support_or_remove:{item}")
    for item in citation_failures + religious_failures:
        revisions.append(f"correct_citation:{item}")

    return VerificationResult(
        passed=not (unsupported or citation_failures or religious_failures or revisions or contradictions),
        unsupported_claims=sorted(set(unsupported)),
        citation_failures=sorted(set(citation_failures)),
        religious_source_failures=sorted(set(religious_failures)),
        contradictions=contradictions,
        required_revisions=sorted(set(revisions)),
    )


def release_gate(verification: VerificationResult, *, revision_count: int) -> ReleaseDecision:
    if verification.passed:
        return ReleaseDecision(release=True, action="publish", verification_status="passed")
    reasons = sorted(set(
        verification.unsupported_claims
        + verification.citation_failures
        + verification.religious_source_failures
        + verification.contradictions
        + verification.required_revisions
    ))
    if revision_count < 1:
        return ReleaseDecision(release=False, action="revise", verification_status="passed_with_caution", reasons=reasons)
    return ReleaseDecision(release=False, action="limited_answer", verification_status="insufficient", reasons=reasons)
