import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from psycopg import Connection

from .schemas import AdapterScore


DEFAULT_MANUAL_SOURCES = [
    {"provider": "OpenAI", "display_name": "OpenAI Flagship", "model_name": "flagship"},
    {"provider": "OpenAI", "display_name": "OpenAI Reasoning", "model_name": "reasoning"},
    {"provider": "Anthropic", "display_name": "Claude Flagship", "model_name": "flagship"},
    {"provider": "Anthropic", "display_name": "Claude Reasoning", "model_name": "reasoning"},
    {"provider": "Google", "display_name": "Gemini Flagship", "model_name": "flagship"},
    {"provider": "DeepSeek", "display_name": "DeepSeek Reasoning", "model_name": "reasoning"},
    {"provider": "Qwen", "display_name": "Qwen Flagship", "model_name": "flagship"},
    {"provider": "Zhipu", "display_name": "GLM Flagship", "model_name": "flagship"},
    {"provider": "Meta", "display_name": "Llama Open", "model_name": "open"},
    {"provider": "Mistral", "display_name": "Mistral", "model_name": "latest"},
    {"provider": "xAI", "display_name": "Grok", "model_name": "latest"},
]

DEFAULT_BENCHMARKS = [
    ("General reasoning", "General reasoning"),
    ("Math", "Math"),
    ("Coding", "Coding"),
    ("Science", "Science"),
    ("Long context", "Long context"),
    ("Multilingual", "Multilingual"),
    ("Arabic capability", "Arabic"),
    ("Tool use", "Tool use"),
    ("Instruction following", "Instruction following"),
    ("Factuality", "Factuality"),
    ("Hallucination resistance", "Hallucination resistance"),
    ("Safety", "Safety"),
    ("Agentic task completion", "Agentic task completion"),
]


@dataclass
class ExternalModelScoreAdapter:
    provider: str

    async def fetch_scores(self) -> list[AdapterScore]:
        return []


class ManualBenchmarkAdapter(ExternalModelScoreAdapter):
    def __init__(self, provider: str | None = None):
        super().__init__(provider or "Manual")

    async def fetch_scores(self) -> list[AdapterScore]:
        scores: list[AdapterScore] = []
        for model in load_manual_sources():
            if self.provider != "Manual" and model["provider"].lower() != self.provider.lower():
                continue
            configured_scores = model.get("scores") or [
                {"benchmark": name, "benchmark_category": category, "score": None}
                for name, category in DEFAULT_BENCHMARKS
            ]
            for item in configured_scores:
                raw_score = item.get("score")
                max_score = item.get("max_score", 100) or 100
                scores.append(
                    AdapterScore(
                        provider=model["provider"],
                        model_name=model.get("model_name", "configurable-latest"),
                        display_name=model.get("display_name", model["provider"]),
                        model_version_or_date=model.get("model_version_or_date"),
                        benchmark=item["benchmark"],
                        benchmark_category=item.get("benchmark_category") or item["benchmark"],
                        score=item.get("score"),
                        max_score=max_score,
                        normalized_score_0_100=normalize_score(raw_score, max_score),
                        source_type=source_type_label(model.get("source_type", "manual")),
                        source_url=model.get("source_url") or None,
                        source_name=model.get("source_name") or "Manual benchmark metadata",
                        published_at=model.get("published_at"),
                        confidence_level=model.get("confidence_level") or "low",
                        notes=model.get("notes") or "No live provider benchmark API configured.",
                        manually_configured=True,
                        raw_payload_json={
                            "source_type": model.get("source_type", "manual"),
                            "loaded_at": datetime.now(UTC).isoformat(),
                            "note": "No provider benchmark API configured; score remains null until manually sourced.",
                        },
                    )
                )
        return scores


class OpenAIModelScoreAdapter(ManualBenchmarkAdapter):
    def __init__(self):
        super().__init__("OpenAI")


class AnthropicModelScoreAdapter(ManualBenchmarkAdapter):
    def __init__(self):
        super().__init__("Anthropic")


class GeminiModelScoreAdapter(ManualBenchmarkAdapter):
    def __init__(self):
        super().__init__("Google")


class DeepSeekModelScoreAdapter(ManualBenchmarkAdapter):
    def __init__(self):
        super().__init__("DeepSeek")


class QwenModelScoreAdapter(ManualBenchmarkAdapter):
    def __init__(self):
        super().__init__("Qwen")


class GLMModelScoreAdapter(ManualBenchmarkAdapter):
    def __init__(self):
        super().__init__("Zhipu")


def load_manual_sources() -> list[dict[str, Any]]:
    config_path = Path(__file__).with_name("external_benchmark_sources.yaml")
    try:
        import yaml  # type: ignore

        if config_path.exists():
            data = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
            return data.get("models", DEFAULT_MANUAL_SOURCES)
    except Exception:
        pass
    return DEFAULT_MANUAL_SOURCES


def adapters_for(provider: str | None = None) -> list[ExternalModelScoreAdapter]:
    adapters: list[ExternalModelScoreAdapter] = [
        OpenAIModelScoreAdapter(),
        AnthropicModelScoreAdapter(),
        GeminiModelScoreAdapter(),
        DeepSeekModelScoreAdapter(),
        QwenModelScoreAdapter(),
        GLMModelScoreAdapter(),
        ManualBenchmarkAdapter("Meta"),
        ManualBenchmarkAdapter("Mistral"),
        ManualBenchmarkAdapter("xAI"),
    ]
    if provider:
        return [adapter for adapter in adapters if adapter.provider.lower() == provider.lower()]
    return adapters


async def refresh_external_scores(conn: Connection, provider: str | None = None) -> dict[str, Any]:
    inserted = 0
    fetched_at = datetime.now(UTC)
    normalized: list[dict[str, Any]] = []
    for adapter in adapters_for(provider):
        for score in await adapter.fetch_scores():
            model = conn.execute(
                """
                insert into eval_models (provider, model_name, display_name, model_family, is_local, api_model_name)
                values (%s,%s,%s,%s,false,%s)
                on conflict (provider, model_name) do update
                set display_name=excluded.display_name,
                    model_family=excluded.model_family,
                    api_model_name=excluded.api_model_name,
                    updated_at=now()
                returning id
                """,
                (score.provider, score.model_name, score.display_name, score.provider, score.model_name),
            ).fetchone()
            benchmark = conn.execute(
                """
                insert into eval_benchmarks (name, category, description, benchmark_type, source_url, source_name)
                values (%s,%s,%s,'external_reported',%s,%s)
                on conflict (name) do update
                set source_url=coalesce(excluded.source_url, eval_benchmarks.source_url),
                    source_name=coalesce(excluded.source_name, eval_benchmarks.source_name),
                    updated_at=now()
                returning id
                """,
                (score.benchmark, score.benchmark, f"External reported or configured score for {score.benchmark}.", score.source_url, score.source_name),
            ).fetchone()
            freshness_status = freshness(score.published_at, fetched_at)
            conn.execute(
                """
                insert into external_model_scores
                (model_id, benchmark_id, score, score_unit, source_url, source_name, confidence_level, fetched_at,
                 manually_configured, raw_payload_json, model_version_or_date, benchmark_category, max_score,
                 normalized_score_0_100, source_type, published_at, notes, freshness_status)
                values (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s::jsonb,%s,%s,%s,%s,%s,%s,%s,%s)
                """,
                (
                    model["id"],
                    benchmark["id"],
                    score.score,
                    score.score_unit,
                    score.source_url,
                    score.source_name,
                    score.confidence_level,
                    fetched_at,
                    score.manually_configured,
                    json.dumps(score.raw_payload_json),
                    score.model_version_or_date,
                    score.benchmark_category or score.benchmark,
                    score.max_score,
                    score.normalized_score_0_100,
                    score.source_type,
                    score.published_at,
                    score.notes,
                    freshness_status,
                ),
            )
            inserted += 1
            normalized.append(score.model_dump())
    return {"inserted": inserted, "fetched_at": fetched_at.isoformat(), "scores": normalized}


def normalize_score(score: float | None, max_score: float = 100) -> float | None:
    if score is None:
        return None
    if max_score <= 0:
        return None
    return round(max(0, min(100, (float(score) / float(max_score)) * 100)), 2)


def freshness(published_at: str | None, fetched_at: datetime | None = None) -> str:
    stamp = published_at
    if not stamp and fetched_at:
        stamp = fetched_at.isoformat()
    if not stamp:
        return "Unknown freshness"
    try:
        parsed = datetime.fromisoformat(stamp.replace("Z", "+00:00"))
    except ValueError:
        return "Unknown freshness"
    age_days = (datetime.now(UTC) - parsed.astimezone(UTC)).days
    if age_days <= 30:
        return "Fresh"
    if age_days <= 90:
        return "Aging"
    return "Stale"


def source_type_label(source_type: str) -> str:
    mapping = {
        "api": "Live API",
        "provider": "Provider-reported",
        "third_party": "Third-party reported",
        "manual": "Manual source",
        "internal": "Internal measurement",
    }
    return mapping.get(source_type, "Unavailable")
