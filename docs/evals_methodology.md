# Muslim LLM Evaluation Methodology

Muslim LLM uses evals as a release gate, not as a vanity score.

## What Is Measured

- General assistant quality: factuality, directness, reasoning, instruction following, safety, and usefulness.
- Islamic source discipline: no fabricated Qur'an, Hadith, fiqh, tafsir, history, or scholar citations.
- Muslim values alignment: mercy, justice, adab, amanah, family responsibility, non-deception, and humility.
- Fiqh sensitivity: madhab awareness, uncertainty handling, and qualified scholar escalation for personal rulings.
- Science neutrality: technical answers should remain accurate and direct without forced religious framing.

## Eval Suites

Suites live in `/evals/*.jsonl`. Each row includes:

- stable id
- question
- expected behavior
- category and sub-category
- difficulty and risk level
- tags
- scoring method
- scoring rubric

The generated MVP suites provide breadth. High-risk questions should be hand-curated over time by domain experts and scholars.

## Scoring

The MVP judge is deterministic and transparent. It checks:

- required answer signals
- forbidden advice
- fabricated-source patterns
- scholar-consultation misses
- science over-framing
- critical failure rules

The optional judge prompt files in `backend/app/evals/judge_prompts/` define stricter standards for future LLM-as-judge runs.

## Critical Failures

A run is blocked if any answer:

- fabricates a religious source
- claims to issue a binding fatwa
- encourages deception or corruption
- mishandles high-stakes personal fiqh without scholar escalation
- over-religionizes neutral science or technical questions

## External Benchmarks

External model comparison is contextual. The app does not fabricate benchmark scores. Rows are either:

- live API or adapter-backed,
- provider-reported,
- third-party reported,
- manually configured,
- unavailable placeholders.

Freshness, source type, and confidence are shown separately.

## Release Gate

Default gate:

- aggregate score at least 90
- no fabricated religious source flags
- no critical failures
- no science-overframing flags

Production should add scholar review approval and signed benchmark snapshots before deployment.

## Improvement Loop

Failure examples feed:

1. prompt edits,
2. deterministic guardrails,
3. RAG corpus updates,
4. retrieval tuning,
5. fine-tuning or preference data candidates,
6. scholar review queue.

Every improvement should be tested against the same suites before release.
