# Reasoning and Speed Release Report

## Production result

Deployed as `2026.07.19-reasoning-speed-r5` on the isolated Muslim LLM stack. The active frontend is `http://148.113.203.232:3200` and the backend health endpoint is `http://148.113.203.232:8200/health`.

The production chat route now creates an assistant placeholder immediately, renders a client-optimistic `Thinking` task, and replaces it with sequenced backend tasks. Reasoning state is separate from Markdown answer content, remains visible while tokens stream, and collapses after completion. Reload ordering is deterministic when user and assistant rows share a timestamp.

## Browser validation

| Prompt | Thinking visible | Visible latency | Task behavior | Result |
|---|---:|---:|---|---|
| What is photosynthesis? | Yes | 35 ms | Science-specific, no retrieval task | Passed |
| Can I lie to close an important sale? | Yes | 28 ms | Honesty, justice, and harm check | Passed |
| How should a traveler pray? | Yes | 33 ms | Fiqh, source, and madhab-sensitive tasks | Passed |
| Write a Python function for binary search. | Yes | 29 ms | Technical tasks, no RAG | Passed |

The mobile viewport (`390x844`) and desktop viewport (`1280x720`) had no horizontal overflow. Prompt-before-answer order also remained correct after a production reload.

## Load validation

The production load profile ran 100 real requests: 50 sequential quick, 20 simultaneous mixed, 20 RAG, and 10 deep requests.

| Metric | Result |
|---|---:|
| Successful answers | 100% |
| Reasoning plan displayed | 100% |
| Silent failures | 0 |
| Empty responses | 0 |
| Stream interruptions | 0 |
| Accepted event p50 / p95 | 58.23 / 280.79 ms |
| Overall first token p50 / p95 | 348.36 / 20,303.52 ms |
| Overall total p50 / p95 | 4,774.72 / 56,599.96 ms |

Warm sequential quick requests reached first token in 114.77 ms p50 and 591.15 ms p95. Twenty simultaneous model-backed requests reached first token in 20,300.05 ms p50 and 20,308.49 ms p95. Deep synthesis completed in 56.60 seconds p50 and 70.03 seconds p95.

The slowest stage is local model generation, averaging 8,971.64 ms. Database prewrite averaged 1.52 ms, classification 0.03 ms, retrieval 0.90 ms, queue wait 116.34 ms, and database finalization 1.50 ms. Ollama remained warm throughout the run.

## Release assessment

The functional release gates pass: every prompt visibly starts, event ordering is canonical, answers stream, optional RAG is conditional, no completed answer is empty, and no request silently disappears. Warm single-user first-token performance exceeds the stated target.

The capacity target does not hold under 20 simultaneous CPU-bound generations. The current two-slot Ollama runtime degrades gracefully and returns answers, but first-token latency rises to about 20 seconds. Improving saturated latency requires more inference capacity, a smaller/faster model, speculative decoding, or a governed overflow provider; it is not a frontend or database bottleneck.

Raw measurements are stored in `work/chat-speed-reasoning-results.json`. Root causes and the corrective architecture are documented in `docs/reasoning_latency_root_cause.md`.
