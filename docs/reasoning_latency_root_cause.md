# Reasoning Visibility and Chat Latency Root Cause

## Audited production path

`frontend/app/page.tsx` creates the user message and assistant placeholder, opens `POST /chat`, parses SSE, and renders `AssistantMessage -> ReasoningProcess` separately from Markdown. The backend persists the user and empty assistant rows, loads recent context, classifies/plans, conditionally retrieves evidence, streams the local Ollama response, validates it, finalizes the assistant row, and emits completion metadata.

## Why Thinking disappeared

1. The optimistic assistant placeholder was mounted correctly, but the first backend plan could replace it with all tasks still pending. `AssistantMessage` previously considered reasoning active only when a task was active, so this race produced an empty assistant block.
2. `ReasoningProcess` collapsed as soon as the first answer token arrived. Real retrieval, writing, and validation updates therefore continued while hidden.
3. Earlier client code simulated a five-stage trace using a three-second timer. Those labels were prompt-sensitive but not tied to backend operations.
4. Backend task events used flat fields, while the requested canonical contract uses a `task` object. There was no shared parser or type contract.
5. Events had no monotonic sequence, so reconnects or duplicated frames could not be rejected safely.
6. The backend emitted duplicate `meta`/`metadata` and `complete`/`done` frames, creating extra state transitions.

## Why responses were slow

1. The backend emitted nothing until after reasoning-plan construction; there was no immediate `accepted` frame.
2. Every query classified as Islamic triggered retrieval before model generation, including simple values guidance that did not need exact sources.
3. Up to 32 messages and 24,000 characters of history were sent on every route.
4. The full system and evidence prompt was used for simple questions.
5. Each model call created a new HTTP client and did not explicitly keep Ollama warm.
6. One universal output-token ceiling was used regardless of request complexity.
7. Required retrieval and planning were serialized.
8. PostgreSQL opened a fresh connection for each bounded operation and lacked request/history indexes. The request did correctly avoid holding a transaction open during generation.
9. The public deployment uses direct ports rather than an Nginx proxy, so proxy buffering was not the active bottleneck. Streaming responses nevertheless lacked explicit anti-buffering headers.

## Corrective architecture

- One sequenced SSE envelope with immediate `accepted`, canonical task objects, one metadata frame, and one completion frame.
- One truthful client-optimistic task until the real plan replaces it; no timer-driven task completion.
- Automatic instant/quick/standard/deep/retrieval routing with conditional RAG and route-specific context/output budgets.
- Concurrent required retrieval and planning, reusable HTTP connection, startup warmup, keep-alive, queue limits, cancellation, and explicit stream-flush headers.
- Privacy-safe performance telemetry at `/diagnostics/chat-performance`.

The visible process contains operation labels only. It never contains hidden chain-of-thought, prompt text, private scratchpads, or internal policy text.

