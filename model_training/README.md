# Muslim LLM Training Platform

This directory is an experimental, evidence-gated model-training platform. It does **not** claim that a large Muslim LLM checkpoint has been trained or that sparse MoE and Muon are already superior.

## Decision being improved

**Decision:** whether Muslim LLM should scale a dense, conventional MoE, or shared-expert MoE architecture, and whether Muon provides a cost-adjusted advantage over AdamW.

**Decision makers:** model research, data governance, product safety, and infrastructure owners.

**Wrong-decision cost:** expensive failed training, unstable inference, expert collapse, loss of general capability, or religious-source errors encoded into weights.

**Human review:** dataset admission, religious integrity, licenses, release-gate exceptions, and every scale transition.

**KPI:** downstream capability and Muslim-domain depth per activated parameter, training dollar, and inference dollar, with no critical general/safety regression.

## What works now

- Decoder-only Transformer with RoPE, grouped-query attention, RMSNorm, and SwiGLU.
- Dense, top-k sparse MoE, and shared-expert MoE variants from one validated config.
- Capacity-controlled dispatch/combine, residual overflow, router z-loss, load-balancing loss, and routing telemetry.
- Muon for eligible hidden matrices and AdamW for embeddings, heads, norms, biases, and routers.
- Atomic, hash-verified checkpoints with optimizer, RNG, cursor, and experiment metadata.
- Governed data registry, auditable quality components, deduplication with scholarly-context preservation, decontamination, curriculum, and capped mixtures.
- Reversible byte tokenizer baseline and multilingual fertility/integrity metrics.
- Tiny training, ablation reports, streaming inference engine, and blocking release gate.

## Run

```bash
cd model_training
python3 -m venv .venv
.venv/bin/pip install -e '.[test]'
.venv/bin/pytest -q
scripts/train_tiny.sh --config configs/model/unit_moe_shared.yaml
scripts/run_ablation_matrix.sh
```

Generated reports live under `experiments/`. Larger configs are design candidates only. Do not instantiate `candidate_moe.yaml` on a workstation.

## Weights versus RAG

Weights learn language, representation, reasoning patterns, general capability, values orientation, and source-aware behavior. Governed RAG remains responsible for exact Qur'an/Hadith references, fiqh attribution and disagreement, historical citations, and current facts.

## Scale boundary

Stage 0 validates mechanisms. Stage 1 requires suitable accelerator hardware and a governed dataset manifest. Stage 2 is prohibited until controlled architecture, optimizer, corpus, curriculum, tokenizer, recovery, and inference-economics gates pass.

