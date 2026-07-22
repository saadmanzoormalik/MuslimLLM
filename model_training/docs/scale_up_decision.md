# Scale-Up Decision

## Current status: Experimental

The local machine can establish functional correctness and tiny-model learning behavior. It cannot establish 100M–3B scaling economics, expert-parallel communication efficiency, multilingual capability, or production quality.

## Required Stage 1 evidence

| Gate | Required evidence | Current state |
|---|---|---|
| Dense comparison | Three seeds, matched activated parameters and tokens | Tiny single-seed run only |
| MoE efficiency | Quality parity or gain at lower activated compute | Not established |
| Muon value | Loss/token and loss/wall-time parity or gain | Tiny run only |
| Governed data | Licensed, versioned corpus with human approvals | Pipeline ready; corpus absent |
| Tokenizer | 32K/64K/100K BPE and unigram multilingual comparison | Byte baseline only |
| Recovery | Multi-rank interruption and restart | Single-rank hash/resume tested |
| Inference | p50/p95/p99 and active-parameter economics | Functional stream only |
| Quality | General + Muslim-domain evaluation matrix | Harness contract only |

## Go criteria

Proceed to 100M–300M only after at least three reproducible seeds show stable routing, zero persistent dead experts, less than 1% dropped tokens, acceptable communication overhead, and no dense-baseline regression under matched activated compute. Proceed to 1B–3B only when governed data and multilingual tokenizer gates also pass.

## Stop criteria

Stop or redesign if routing collapses, Muon introduces instability, sparse communication removes the compute benefit, Muslim-domain training causes general/science regression, religious attribution checks fail, or checkpoint recovery is not exact.

