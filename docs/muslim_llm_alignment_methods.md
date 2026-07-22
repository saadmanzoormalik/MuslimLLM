# Muslim LLM Alignment Methods

This MVP uses local behavioral specialization rather than GPU weight-level fine-tuning.

## Implemented Locally

1. Constitutional alignment prompt
   - Defines Muslim values, scholarly humility, citation integrity, and refusal behavior.
   - Applies across ordinary life, business, family, politics, technology, and Islamic topics.

2. Local Ollama model specialization
   - Created as `muslim-llm-local` from `qwen2.5:1.5b`.
   - Uses a stronger system constitution and conservative generation parameters.

3. RAG-first grounding
   - Islamic/civilizational questions retrieve local corpus evidence before generation.
   - The model is instructed not to fabricate Quran, Hadith, fiqh, tafsir, or historical citations.

4. Evidence-level separation
   - The answer policy distinguishes Quran, Hadith, Tafsir, Fiqh, History, Modern opinion, and Geopolitical analysis.

5. Evaluation dataset
   - `evals/muslim_values_alignment.jsonl` contains checks for ordinary life, business ethics, fiqh humility, history, general capability, citation integrity, geopolitics, and personal religious rulings.

6. Deterministic constitutional guardrails
   - `backend/app/alignment.py` catches clear deception, fraud, corruption, and fabricated religious proof requests before generation.
   - This is necessary because small local models can ignore prompt-only ethical instructions.

## Not Yet Done

Weight-level fine-tuning was not run in this MVP. A real fine-tune would require:
- curated instruction data,
- rejected/preferred answer pairs,
- scholar or domain expert review,
- LoRA or QLoRA training,
- DPO or another preference optimization pass,
- regression tests against hallucination, sectarianism, over-refusal, and general utility.

## Recommended Production Path

1. Collect high-quality SFT examples.
2. Train a LoRA/QLoRA adapter.
3. Build preference pairs from human review.
4. Run DPO or equivalent preference optimization.
5. Run retrieval-grounded evals and red-team tests.
6. Deploy only after governance approval.
