from __future__ import annotations

from collections import Counter
from typing import Any

from .schemas import EvidencePack, EvidenceSource, QueryPolicy, RetrievalJob


REQUIRED_METADATA: dict[str, list[str]] = {
    "QURAN_VERIFIED": ["source_type", "surah", "ayah", "language", "translator", "edition", "authority_tier", "dataset_version"],
    "HADITH_VERIFIED": ["collection", "book", "chapter", "hadith_number", "grader", "grading", "edition", "authority_tier", "dataset_version"],
    "TAFSIR_AND_CLASSICAL_SCHOLARSHIP": ["title", "author", "school", "century", "source_type", "language", "edition", "authority_tier", "dataset_version"],
    "FIQH_AND_USUL": ["madhab", "topic", "ruling_type", "scholar", "jurisdiction", "historical_period", "authority_tier", "dataset_version"],
    "ISLAMIC_HISTORY_AND_CIVILIZATION": ["period", "geography", "source_type", "primary_or_secondary", "author", "publication_date", "authority_tier", "dataset_version"],
    "MODERN_MUSLIM_WORLD": ["source_type", "author", "publication_date", "authority_tier", "dataset_version"],
    "GENERAL_SCIENCE_AND_ACADEMIC": ["source_type", "author", "publication_date", "authority_tier", "dataset_version"],
    "LIVE_RESEARCH_CANDIDATES": ["source_type", "author", "publication_date", "authority_tier", "dataset_version", "copyright_status"],
}


def _job(name: str, top_k: int, policy: QueryPolicy, **kwargs: Any) -> RetrievalJob:
    return RetrievalJob(
        knowledge_base=name,
        top_k=top_k,
        required_metadata=REQUIRED_METADATA[name],
        minimum_authority_tier=policy.minimum_source_tier,
        **kwargs,
    )


def build_retrieval_plan(policy: QueryPolicy, *, specified_madhab: str | None = None) -> list[RetrievalJob]:
    jobs: list[RetrievalJob] = []
    names: set[str] = set()

    def add(job: RetrievalJob) -> None:
        if job.knowledge_base not in names:
            jobs.append(job)
            names.add(job.knowledge_base)

    if policy.quran_required:
        add(_job("QURAN_VERIFIED", 5, policy))
    if policy.hadith_required:
        add(_job("HADITH_VERIFIED", 8, policy))
    if policy.fiqh_sensitive:
        filters = {"madhab": specified_madhab} if specified_madhab else {}
        add(_job("FIQH_AND_USUL", 8, policy, metadata_filters=filters))
        add(_job("QURAN_VERIFIED", 5, policy, required=False))
        add(_job("HADITH_VERIFIED", 8, policy, required=False))
    if policy.historical_sources_required:
        add(_job("ISLAMIC_HISTORY_AND_CIVILIZATION", 8, policy))
    if policy.current_sources_required:
        add(_job("MODERN_MUSLIM_WORLD", 8, policy))
        add(_job("LIVE_RESEARCH_CANDIDATES", 8, policy, live=True, required=True))
    if policy.scientific_sources_required:
        add(_job("GENERAL_SCIENCE_AND_ACADEMIC", 8, policy))
    if policy.answer_mode == "islamic_knowledge" and not jobs:
        add(_job("TAFSIR_AND_CLASSICAL_SCHOLARSHIP", 6, policy))
        add(_job("ISLAMIC_HISTORY_AND_CIVILIZATION", 6, policy, required=False))
    return jobs


def _source_rejection(source: EvidenceSource, job_by_name: dict[str, RetrievalJob]) -> str | None:
    job = job_by_name.get(source.knowledge_base)
    if not job:
        return "unplanned_knowledge_base"
    if source.disabled:
        return "source_disabled"
    if source.quarantined and source.knowledge_base != "LIVE_RESEARCH_CANDIDATES":
        return "quarantined_source_in_stable_evidence"
    if source.prompt_injection_detected:
        return "source_prompt_injection"
    if source.authority_tier < job.minimum_authority_tier:
        return "authority_tier_below_policy"
    missing = [field for field in job.required_metadata if source.metadata.get(field) in (None, "")]
    if missing:
        return "missing_metadata:" + ",".join(missing)
    return None


def evaluate_evidence(
    policy: QueryPolicy,
    retrieval_jobs: list[RetrievalJob],
    sources: list[EvidenceSource],
    *,
    conflicts: list[str] | None = None,
) -> EvidencePack:
    jobs = {job.knowledge_base: job for job in retrieval_jobs}
    accepted: list[EvidenceSource] = []
    rejected: list[str] = []
    for source in sources:
        reason = _source_rejection(source, jobs)
        if reason:
            rejected.append(f"{source.source_id}:{reason}")
        else:
            accepted.append(source)

    required_jobs = {job.knowledge_base for job in retrieval_jobs if job.required}
    covered_jobs = {source.knowledge_base for source in accepted}
    job_coverage = len(required_jobs & covered_jobs) / max(len(required_jobs), 1) if required_jobs else 1.0
    count_coverage = min(1.0, len(accepted) / max(policy.minimum_source_count, 1)) if policy.minimum_source_count else 1.0
    tiers = [source.authority_tier for source in accepted]
    authority_coverage = min(1.0, (sum(tiers) / len(tiers)) / 5.0) if tiers else (1.0 if not retrieval_jobs else 0.0)
    diversity_keys = {(source.metadata.get("author"), source.metadata.get("source_type")) for source in accepted}
    diversity_ok = not policy.source_diversity_required or len(diversity_keys) >= 2
    coverage_score = round((job_coverage * 0.45) + (count_coverage * 0.35) + (authority_coverage * 0.20), 3)
    if not diversity_ok:
        coverage_score = round(max(0, coverage_score - 0.2), 3)

    conflict_list = conflicts or []
    if coverage_score >= 0.85 and not conflict_list:
        confidence = "high"
    elif coverage_score >= 0.65:
        confidence = "medium"
    elif coverage_score >= 0.4:
        confidence = "low"
    else:
        confidence = "insufficient"
    if policy.minimum_source_count and len(accepted) < policy.minimum_source_count:
        confidence = "insufficient"
    if required_jobs - covered_jobs:
        confidence = "insufficient"
    if not diversity_ok:
        rejected.append("source_diversity_requirement_not_met")

    return EvidencePack(
        sources=accepted,
        coverage_score=coverage_score,
        conflicts=conflict_list,
        evidence_confidence=confidence,
        rejection_reasons=rejected,
    )
