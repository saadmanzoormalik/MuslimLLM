# Stage 0 Go/No-Go Report

## Decision

**Stage 0 mechanism validation: GO.**

**Stage 1 architecture selection and 100M–300M training: NO-GO pending governed data, multilingual tokenizer experiments, accelerator hardware, and matched-compute downstream evaluation.**

No Stage 2 architecture has been selected.

## Three-seed synthetic ablation

| Variant | Mean loss reduction | Std. dev. | Tokens/sec | Total params | Activated estimate |
|---|---:|---:|---:|---:|---:|
| Dense + AdamW | 0.0782 | 0.0322 | 5,216 | 119,104 | 119,104 |
| Dense + hybrid Muon | 0.2236 | 0.0701 | 4,812 | 119,104 | 119,104 |
| MoE + AdamW | 0.0812 | 0.0686 | 4,393 | 205,632 | 131,904 |
| MoE + hybrid Muon | 0.2109 | 0.1359 | 2,631 | 205,632 | 131,904 |
| Shared MoE + hybrid Muon | 0.2037 | 0.1194 | 2,567 | 181,056 | 131,904 |

These are tiny CPU measurements on a synthetic modular-token task. They validate execution and expose tradeoffs; they do not predict 100M+ model quality.

## Findings

1. Muon hybrid produced larger short-horizon loss reduction than AdamW for all matched architectures, but CPU throughput fell substantially.
2. Sparse capacity did not beat the dense hybrid baseline on this task.
3. Shared-expert MoE retained the same activated estimate as conventional MoE with fewer total parameters and showed strong routing entropy with no dropped tokens in the initial run.
4. Router, dispatch, auxiliary loss, optimizer partition, checkpoint resume, data governance, and release blocking are functionally validated.

## Next controlled experiment

Use three or more seeds on accelerator hardware, matched activated parameters, a small governed multilingual corpus, and 32K/64K tokenizer candidates. Compare loss/token, loss/wall-time, downstream general and Muslim-domain evaluations, router balance, communication overhead, and recovery. Shared-expert MoE is a hypothesis, not the selected production architecture.
