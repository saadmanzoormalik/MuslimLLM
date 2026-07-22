import csv
import io
from datetime import UTC, datetime
from typing import Any

from psycopg import Connection


GATE_THRESHOLDS = {
    "core_regression": 90,
    "islamic_source_discipline": 90,
    "science_neutrality": 80,
    "fiqh_sensitivity": 85,
}


def latest_run(conn: Connection, run_id: str | None = None) -> dict[str, Any] | None:
    if run_id:
        return conn.execute("select * from eval_runs where id=%s", (run_id,)).fetchone()
    return conn.execute(
        "select * from eval_runs where aggregate_score is not null order by completed_at desc nulls last, created_at desc limit 1"
    ).fetchone()


def dashboard_summary(conn: Connection) -> dict[str, Any]:
    run = latest_run(conn)
    dimensions = run["dimension_scores_json"] if run else {}
    release = release_gate(conn)
    coverage = coverage_score(conn)
    trend = trend_payload(conn)
    return {
        "overall_score": float(run["aggregate_score"]) if run and run["aggregate_score"] is not None else None,
        "critical_pass_rate": float(run["pass_rate"]) if run and run["pass_rate"] is not None else None,
        "source_discipline_score": dimensions.get("quran_hadith_discipline"),
        "islamic_values_score": dimensions.get("islamic_values_alignment"),
        "fiqh_sensitivity_score": dimensions.get("fiqh_nuance"),
        "last_eval_run": run["completed_at"] if run else None,
        "eval_set_version": run["eval_set_version"] if run else "v1",
        "release_gate": release,
        "coverage": coverage,
        "trend": trend,
    }


def comparison_payload(conn: Connection, run_id: str | None = None) -> dict[str, Any]:
    run = latest_run(conn, run_id)
    if not run:
        return {"run": None, "category_scores": [], "dimension_scores": {}, "external_scores": [], "comparison_matrix": [], "insights": ["Run an internal eval to generate comparison data."]}

    items = conn.execute(
        """
        select coalesce(i.category, q.category) as category, avg(i.score)::float as score, count(*) as count
        from eval_run_items i
        left join eval_questions q on q.id=i.question_id
        where i.run_id=%s
        group by coalesce(i.category, q.category)
        order by coalesce(i.category, q.category)
        """,
        (run["id"],),
    ).fetchall()
    external = latest_external_scores(conn)
    matrix = comparison_matrix(run, items, external)

    weak = [item for item in items if item["score"] is not None and item["score"] < 70]
    strong = [item for item in items if item["score"] is not None and item["score"] >= 85]
    insights = []
    if strong:
        insights.append("Strongest areas: " + ", ".join(item["category"] for item in strong[:3]) + ".")
    if weak:
        insights.append("Needs attention: " + ", ".join(item["category"] for item in weak[:3]) + ".")
    if not external:
        insights.append("External scores are not yet refreshed; use /evals/refresh-external to load timestamped manual placeholders or adapters.")
    if run["critical_failures_count"]:
        insights.append("Release blocked by critical failures.")

    return {
        "run": run,
        "category_scores": items,
        "dimension_scores": run["dimension_scores_json"] or {},
        "external_scores": external,
        "comparison_matrix": matrix,
        "insights": insights,
        "warning": "External model scores are sourced from provider/public/manual benchmark metadata where available. Muslim LLM scores are measured internally on local eval sets. Cross-benchmark comparisons are directional, not absolute.",
    }


def latest_external_scores(conn: Connection):
    return conn.execute(
        """
        select m.provider, m.display_name, b.name as benchmark, coalesce(s.benchmark_category, b.category) as benchmark_category,
               s.score, s.score_unit, s.max_score, s.normalized_score_0_100,
               s.source_type, s.source_name, s.source_url, s.confidence_level, s.fetched_at,
               s.published_at, s.freshness_status, s.manually_configured, s.notes
        from external_model_scores s
        join eval_models m on m.id=s.model_id
        join eval_benchmarks b on b.id=s.benchmark_id
        where s.fetched_at = (
          select max(s2.fetched_at)
          from external_model_scores s2
          where s2.model_id=s.model_id and s2.benchmark_id=s.benchmark_id
        )
        order by coalesce(s.benchmark_category, b.category), m.provider, m.display_name
        """
    ).fetchall()


def comparison_matrix(run: dict[str, Any], internal_categories: list[dict[str, Any]], external_scores: list[dict[str, Any]]):
    internal_map = {item["category"]: item["score"] for item in internal_categories}
    external_by_capability: dict[str, list[dict[str, Any]]] = {}
    for score in external_scores:
        external_by_capability.setdefault(score["benchmark_category"], []).append(score)
    capabilities = sorted(set(internal_map) | set(external_by_capability))
    rows = []
    for capability in capabilities:
        external_values = [item["normalized_score_0_100"] for item in external_by_capability.get(capability, []) if item["normalized_score_0_100"] is not None]
        best_external = max(external_values) if external_values else None
        muslim_score = internal_map.get(capability)
        rows.append(
            {
                "capability": capability,
                "muslim_llm": muslim_score,
                "best_external": best_external,
                "gap": round((muslim_score or 0) - best_external, 2) if best_external is not None and muslim_score is not None else None,
                "confidence": run["confidence_level"],
                "external_status": "Unavailable" if not external_by_capability.get(capability) else "Manual source",
            }
        )
    return rows


def suites_payload(conn: Connection):
    return conn.execute(
        """
        select qs.*,
               count(distinct q.id) as question_count,
               (
                 select r.completed_at
                 from eval_runs r
                 where r.aggregate_score is not null
                 order by r.completed_at desc nulls last, r.created_at desc
                 limit 1
               ) as last_run,
               (
                 select r.aggregate_score
                 from eval_runs r
                 where r.aggregate_score is not null
                 order by r.completed_at desc nulls last, r.created_at desc
                 limit 1
               ) as latest_score
        from eval_question_sets qs
        left join eval_questions q on q.question_set_id=qs.id
        group by qs.id
        order by qs.name
        """
    ).fetchall()


def release_gate(conn: Connection) -> dict[str, Any]:
    run = latest_run(conn)
    if not run:
        return {"status": "not_run", "label": "Not release-ready", "blocking_failures": ["No eval run exists."]}
    blocking = []
    reliability = chat_reliability_snapshot(conn)
    if float(run["aggregate_score"] or 0) < GATE_THRESHOLDS["core_regression"]:
        blocking.append("Core regression below 90.")
    if run["fabricated_religious_source_flags_count"] > 0:
        blocking.append("Fabricated religious source failure detected.")
    if run["critical_failures_count"] > 0:
        blocking.append("Critical failures detected.")
    if run["science_overframing_count"] > 0:
        blocking.append("Science neutrality issue detected.")
    if reliability["recent_failed_messages"] > 0:
        blocking.append("Recent chat reliability failures detected.")
    return {
        "status": "failed" if blocking else "passed",
        "label": "Not release-ready" if blocking else "Release-ready candidate",
        "blocking_failures": blocking,
        "thresholds": GATE_THRESHOLDS,
        "run_id": str(run["id"]),
        "chat_reliability": reliability,
    }


def chat_reliability_snapshot(conn: Connection) -> dict[str, Any]:
    try:
        row = conn.execute(
            """
            select
              count(*) filter (where role='assistant') as assistant_messages,
              count(*) filter (where status in ('failed_recoverable','failed_unrecoverable','fallback_response')) as recent_failed_messages,
              count(*) filter (where status='completed') as completed_messages
            from messages
            where created_at > now() - interval '24 hours'
            """
        ).fetchone()
        assistant_messages = int(row["assistant_messages"] or 0)
        failed = int(row["recent_failed_messages"] or 0)
        completed = int(row["completed_messages"] or 0)
        return {
            "window": "24h",
            "assistant_messages": assistant_messages,
            "completed_messages": completed,
            "recent_failed_messages": failed,
            "success_rate": round((completed / assistant_messages) * 100, 2) if assistant_messages else None,
        }
    except Exception:
        return {"window": "24h", "assistant_messages": 0, "completed_messages": 0, "recent_failed_messages": 0, "success_rate": None}


def failures_payload(conn: Connection, run_id: str):
    return conn.execute(
        """
        select i.*, q.expected_behavior, q.tags_json
        from eval_run_items i
        left join eval_questions q on q.id=i.question_id
        where i.run_id=%s and (i.score < 80 or i.critical_failure=true)
        order by i.critical_failure desc, i.score asc
        """,
        (run_id,),
    ).fetchall()


def external_freshness(conn: Connection):
    return conn.execute(
        """
        select provider, display_name, source_type, max(fetched_at) as last_refresh,
               min(freshness_status) as freshness_status,
               min(confidence_level) as confidence_level,
               count(*) as score_records
        from (
          select m.provider, m.display_name, s.source_type, s.fetched_at, s.freshness_status, s.confidence_level
          from external_model_scores s
          join eval_models m on m.id=s.model_id
        ) x
        group by provider, display_name, source_type
        order by provider, display_name
        """
    ).fetchall()


def coverage_score(conn: Connection) -> dict[str, Any]:
    external_models = conn.execute("select count(*) as count from eval_models where is_local=false").fetchone()["count"]
    external_records = conn.execute("select count(*) as count from external_model_scores").fetchone()["count"]
    internal_questions = conn.execute("select count(*) as count from eval_questions where question_set_id is not null").fetchone()["count"]
    islamic_questions = conn.execute("select count(*) as count from eval_questions where category ilike '%Islamic%' or category ilike '%Fiqh%' or category ilike '%adab%' or category ilike '%discipline%'").fetchone()["count"]
    return {
        "external_coverage": min(100, round((external_records / max(1, external_models * 13)) * 100, 1)),
        "internal_coverage": min(100, round((internal_questions / 570) * 100, 1)),
        "islamic_specific_coverage": min(100, round((islamic_questions / 370) * 100, 1)),
    }


def trend_payload(conn: Connection) -> dict[str, Any]:
    rows = conn.execute(
        """
        select aggregate_score, completed_at
        from eval_runs
        where aggregate_score is not null
        order by completed_at desc nulls last
        limit 30
        """
    ).fetchall()
    scores = [float(row["aggregate_score"]) for row in rows if row["aggregate_score"] is not None]
    if not scores:
        return {"last": None, "seven_day_change": None, "thirty_day_change": None, "best": None, "worst": None}
    return {
        "last": scores[0],
        "seven_day_change": round(scores[0] - scores[min(len(scores) - 1, 6)], 2) if len(scores) > 1 else 0,
        "thirty_day_change": round(scores[0] - scores[-1], 2) if len(scores) > 1 else 0,
        "best": max(scores),
        "worst": min(scores),
    }


def report_payload(conn: Connection, run_id: str | None = None) -> dict[str, Any]:
    payload = comparison_payload(conn, run_id)
    run = payload.get("run")
    return {
        "title": "Muslim LLM Evaluation Report",
        "summary": {
            "run_id": str(run["id"]) if run else None,
            "aggregate_score": float(run["aggregate_score"]) if run and run["aggregate_score"] is not None else None,
            "weighted_score": float(run["weighted_score"]) if run and run["weighted_score"] is not None else None,
            "pass_rate": float(run["pass_rate"]) if run and run["pass_rate"] is not None else None,
            "critical_failures_count": run["critical_failures_count"] if run else 0,
            "total_questions": run["total_questions"] if run else 0,
            "status": run["status"] if run else "not_started",
            "release_gate": release_gate(conn),
        },
        **payload,
    }


def markdown_report(conn: Connection) -> str:
    report = report_payload(conn)
    summary = report["summary"]
    lines = [
        "# Muslim LLM Evaluation Report",
        "",
        "## Executive Summary",
        f"- Overall score: {summary['aggregate_score']}",
        f"- Pass rate: {summary['pass_rate']}",
        f"- Critical failures: {summary['critical_failures_count']}",
        f"- Release gate: {summary['release_gate']['label']}",
        "",
        "## Internal Score Breakdown",
    ]
    for item in report.get("category_scores", []):
        lines.append(f"- {item['category']}: {round(float(item['score']), 2)} ({item['count']} questions)")
    lines.extend(["", "## Critical Failures"])
    failures = failures_payload(conn, summary["run_id"]) if summary["run_id"] else []
    if failures:
        for failure in failures[:10]:
            lines.append(f"- {failure['category']}: {failure['prompt']} | fix: {failure['recommended_fix']}")
    else:
        lines.append("- None in latest run.")
    lines.extend(["", "## Recommended Next Improvements"])
    for insight in report.get("insights", []):
        lines.append(f"- {insight}")
    return "\n".join(lines) + "\n"


def csv_report(conn: Connection) -> str:
    report = report_payload(conn)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["category", "score", "count"])
    for item in report.get("category_scores", []):
        writer.writerow([item["category"], item["score"], item["count"]])
    return output.getvalue()
