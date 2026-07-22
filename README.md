# Muslim LLM

Muslim LLM is a production-style MVP for a general-purpose chat assistant with an Islamic-civilizational knowledge layer. It behaves like a modern LLM chat product for normal questions, and uses retrieved Islamic/civilizational sources first when the topic touches Islam, Muslim history, jurisprudence, governance, trade, science, culture, ethics, or geopolitics.

It is not a fatwa bot. The system prompt requires scholarly humility, source separation, madhab awareness where relevant, and explicit refusal to fabricate Quran, Hadith, fiqh, or historical citations.

## Architecture

Browser UI -> Next.js + Tailwind -> FastAPI -> PostgreSQL + pgvector -> RAG retrieval -> local/open-source OpenAI-compatible LLM -> citations -> evaluation dashboard

Core services:

- `frontend/`: Next.js app with chat, history sidebar, streaming responses, markdown, copy, regenerate, stop generation, source drawer, document admin, settings, and evaluations.
- `backend/`: FastAPI API with chat, document ingestion, pgvector retrieval, source search, settings, auth-ready users, and eval endpoints.
- `backend/app/evals/`: standalone evals-dashboard backend with model registry, benchmark adapters, internal eval runner, comparisons, and reports.
- `backend/app/imports/`: context import backend with provider adapters, local parsing, preview, coverage, memory review, reports, and audit logging.
- `postgres/init.sql`: PostgreSQL schema with pgvector.
- `data/`: small public-domain/sample seed documents.
- `muslim_llm_system_prompt.md`: default assistant behavior prompt.

## Run Locally

1. Copy environment values:

```bash
cp .env.example .env
```

2. Run a lower-cost local open-source model with Ollama:

```bash
ollama pull qwen2.5:1.5b
ollama serve
```

The backend defaults to Ollama's OpenAI-compatible endpoint. The connection can also be changed from **Settings -> AI Context Sync -> Connect model** without restarting the app:

```bash
LLM_API_BASE=http://127.0.0.1:11434/v1
LLM_MODEL=muslim-llm-local
LLM_API_KEY=
LLM_MAX_TOKENS=700
```

The UI still shows Muslim LLM as its own product. The backend privately maps that product model to the configured open-source model.

For Docker, the optional Ollama service is available with:

```bash
docker compose --profile local-llm up --build
```

Then pull the model once:

```bash
docker compose exec ollama ollama pull qwen2.5:1.5b
```

If the local model is not running, the backend falls back to deterministic local MVP behavior instead of breaking the chat.

To use a hosted OpenAI-compatible provider, use the in-app connection flow or override:

```bash
LLM_API_BASE=https://provider.example.com/v1
LLM_API_KEY=your_key
LLM_MODEL=provider-model-name
```

Remote endpoints must use HTTPS. API keys are encrypted before storage and are never returned by the API. Local Ollama connections need no credential and keep prompts on this machine. Keep `CONTEXT_SYNC_TOKEN_KEY` stable across restarts so saved credentials remain decryptable.

3. Start the stack:

```bash
docker compose up --build
```

4. Open:

- Frontend: http://localhost:3000
- Backend health: http://localhost:8000/health

Seed documents from `/data` are indexed automatically on first backend startup if the database has no documents.

## Main API Endpoints

- `POST /chat`
- `GET /chats`
- `GET /chats/{id}`
- `DELETE /chats/{id}`
- `POST /documents/upload`
- `GET /documents`
- `DELETE /documents/{id}`
- `POST /documents/reindex`
- `GET /sources/search`
- `POST /eval/questions`
- `GET /eval/questions`
- `POST /eval/run`
- `GET /evals/models`
- `GET /evals/benchmarks`
- `POST /evals/run`
- `GET /evals/runs`
- `POST /evals/refresh-external`
- `GET /evals/compare`
- `POST /evals/compare`
- `GET /evals/report`
- `GET /imports/providers`
- `POST /imports/connect/{provider}`
- `POST /imports/upload/{provider}`
- `POST /imports/paste`
- `GET /imports/jobs`
- `GET /imports/jobs/{id}/preview`
- `POST /imports/jobs/{id}/confirm`
- `GET /imports/jobs/{id}/coverage`
- `GET /imports/jobs/{id}/report`
- `GET /imports/memory-suggestions`
- `POST /imports/memory-suggestions/{id}/accept`
- `POST /imports/memory-suggestions/{id}/reject`
- `POST /imports/revoke/{provider}`
- `GET /context-sync/model-connections/active`
- `POST /context-sync/model-connections/test`
- `POST /context-sync/model-connections`
- `DELETE /context-sync/model-connections/{id}`
- `GET /settings`
- `POST /settings`

Auth-ready MVP endpoints are also included:

- `POST /auth/register`
- `POST /auth/login`

## RAG Metadata

Documents support:

- `title`
- `author`
- `source_type`
- `madhab`
- `period`
- `geography`
- `language`
- `reference`
- `reliability_level`
- `copyright_status`
- `uploaded_by`
- `created_at`

Supported uploads:

- `.txt`
- `.md`
- `.pdf`
- `.json`
- `.csv`

## Evaluation Fields

The evaluation system tracks:

- citation accuracy
- hallucination risk
- Islamic nuance
- madhab awareness
- historical accuracy
- general usefulness
- refusal correctness
- overall score
- source discipline
- science neutrality
- critical failure count
- release gate status
- benchmark freshness

The MVP uses transparent deterministic scoring plus named judge prompt files in `backend/app/evals/judge_prompts/`. Production should add calibrated LLM judges, LangSmith datasets, scholar review, and signed release approvals.

## Evals Dashboard

Open `/evals-dashboard` for the standalone evaluation product surface.

It compares:

- general model categories such as reasoning, math, coding, instruction following, factuality, Arabic, safety, and hallucination resistance
- Muslim LLM-specific categories such as Qur'an citation discipline, Hadith citation discipline, fiqh nuance, madhab awareness, family/social adab, Islamic business ethics, and fabricated religious proof prevention

External model scores are not hardcoded as truth. The backend uses provider adapter classes plus `backend/app/evals/external_benchmark_sources.yaml`. If a provider has no configured live benchmark API, the dashboard records timestamped manual-source placeholders with `score: null`, source metadata, and confidence level. Use “Refresh external” to write the latest adapter/manual metadata.

Use “Run eval” to execute a bounded local run against `muslim-llm-local`; answers, rubric scores, latency, token estimates, aggregate score, category rollups, comparison payloads, release gates, failure queues, and reports are stored in PostgreSQL.

Main eval routes:

- `GET /evals/dashboard-summary`
- `GET /evals/suites`
- `POST /evals/run`
- `GET /evals/runs`
- `GET /evals/runs/{run_id}/failures`
- `POST /evals/refresh-external`
- `GET /evals/external-freshness`
- `GET /evals/compare`
- `GET /evals/release-gate`
- `GET /evals/report/latest.json`
- `GET /evals/report/latest.csv`
- `GET /evals/report/latest.md`
- `POST /evals/scholar-review/{run_item_id}`

Methodology is documented in `docs/evals_methodology.md`.

## Import Context

Open `/settings/import-context` to bring your AI context from another assistant into Muslim LLM.

Supported MVP paths:

- ChatGPT export upload, including `conversations.json` or ZIPs containing it.
- Claude/Gemini/DeepSeek/Grok/Qwen/GLM generic JSON, Markdown, text, or CSV uploads.
- Generic JSON project-folder style imports.
- Generic pasted transcripts.

Provider history import is enabled only when an official OAuth and conversation-history API has been configured and verified. Unsupported providers are shown as `Coming soon`; Muslim LLM never requests consumer passwords, browser cookies, or copied session tokens.

Model connection and history import are intentionally separate. An OpenAI-compatible API connection powers new Muslim LLM answers, but it does not grant access to a consumer assistant's existing chat history.

Coverage score means how much context was available and preserved across chats, messages, projects, files, preferences, metadata, attachments, and summaries. Missing provider fields reduce coverage instead of being guessed.

Imported chats appear under All Chats. Imported projects appear under Projects. Chats assigned to projects remain visually listed in All Chats, preserving the current sidebar UX.

Imported memories are suggestions only. Review them in the Import Context page before accepting or rejecting them.

### Transfer Context demo

The production-shaped authorization flow can be tested locally without claiming unsupported commercial history APIs:

```bash
chmod +x deployment/context-sync-macos/*.sh
./deployment/context-sync-macos/start-all.sh
```

Open `http://127.0.0.1:3000/context-sync` and select **Demo AI Account**. Authorization uses PKCE, hashed state, a separate broker, and a one-time grant encrypted to the Mac's device key. Provider context then travels directly from the provider to the Mac; the broker never receives chat content. Commercial provider tiles use official export ingestion where supported and remain explicitly non-direct.

Docs:

- `docs/context_import_architecture.md`
- `docs/provider_import_capabilities.md`
- `docs/import_privacy_and_security.md`
- `docs/context_sync_cloud_auth_architecture.md`
- `docs/context_sync_oauth_security.md`
- `docs/context_sync_device_callbacks.md`
- `docs/context_sync_provider_limitations.md`
- `docs/context_sync_macbook_demo.md`
- `docs/context_sync_production_deployment.md`
- `docs/context_sync_privacy_data_flow.md`

## Production Next Steps

- Add real authentication sessions and per-user authorization.
- Add licensed/public-domain Quran, Hadith, tafsir, fiqh, and history corpora with exact references.
- Add hybrid search, metadata filters, reranking, and citation span validation.
- Add LangSmith traces and eval datasets.
- Add moderation, audit logs, and tenant-level access controls.
- Add deployment secrets management and persistent object storage for uploaded files.
