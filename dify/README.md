# Muslim Knowledge Fabric

This directory contains the portable Dify 1.16 application DSL, governed knowledge-base schema, and deployment manifests for Muslim Knowledge Fabric.

## Safety State

The portable DSL is not self-publishing. On the VPS, the runtime binder injects real dataset and workflow-tool IDs, keeps the quarantine corpus out of the serving graph, and publishes only through the explicit `--publish` release command after draft testing.

## Build

```bash
backend/.venv/bin/python dify/build_apps.py
backend/.venv/bin/python work/test_muslim_knowledge_fabric.py
```

## Runtime Boundary

- Dify is a private orchestration control plane.
- FastAPI remains the public application API.
- Ollama remains local to the Muslim LLM Docker network.
- Dify application keys and model credentials stay server-side.
- `LIVE_RESEARCH_CANDIDATES` is quarantine-only and cannot satisfy stable-source requirements without governance approval.

## Required Publication Order

1. Create and test all eight knowledge bases.
2. Import the twelve specialist workflows.
3. Configure the pinned Ollama provider, the public `muslim-llm-local` model, and the neutral local `qwen2.5:1.5b` fabric model.
4. Publish specialist workflows using `tool-publication.yaml`.
5. Render the main Chatflow with runtime dataset and workflow-tool IDs.
6. Run the eight required queries plus prompt-injection and citation-fabrication tests.
7. Publish the main Chatflow only when every release condition passes.

The deployed network uses policy-aware reviewer gates. Irrelevant reviewers return a deterministic not-applicable result without invoking the model; relevant Islamic-source, fiqh, science, history, or values reviewers remain independent workflow tools.
