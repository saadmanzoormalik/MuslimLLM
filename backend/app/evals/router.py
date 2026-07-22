import json

from fastapi import APIRouter, Depends, HTTPException, Response

from ..auth.sessions import require_principal
from ..db import get_conn
from .external_scores import refresh_external_scores
from .models import init_eval_schema, seed_eval_defaults
from .question_sets import list_question_sets, list_questions
from .reporting import (
    comparison_payload,
    csv_report,
    dashboard_summary,
    external_freshness,
    failures_payload,
    markdown_report,
    release_gate,
    report_payload,
    suites_payload,
)
from .runner import run_internal_eval
from .schemas import CompareRequest, EvalRunRequest, RefreshExternalRequest, ScholarReviewRequest


router = APIRouter(prefix="/evals", tags=["evals-dashboard"], dependencies=[Depends(require_principal)])


def ensure_evals_ready() -> None:
    with get_conn() as conn:
        init_eval_schema(conn)
        seed_eval_defaults(conn)


@router.get("/models")
def eval_models():
    with get_conn() as conn:
        return conn.execute("select * from eval_models order by is_local desc, provider, display_name").fetchall()


@router.get("/benchmarks")
def eval_benchmarks():
    with get_conn() as conn:
        return {
            "benchmarks": conn.execute("select * from eval_benchmarks order by benchmark_type, category, name").fetchall(),
            "question_sets": list_question_sets(conn),
            "questions": list_questions(conn),
        }


@router.get("/dashboard-summary")
def eval_dashboard_summary():
    with get_conn() as conn:
        return dashboard_summary(conn)


@router.post("/run")
async def eval_run(payload: EvalRunRequest):
    with get_conn() as conn:
        result = await run_internal_eval(
            conn,
            model_id=payload.model_id,
            question_set_id=payload.question_set_id,
            run_name=payload.run_name,
            temperature=payload.temperature,
            max_questions=payload.max_questions,
            use_llm_judge=payload.use_llm_judge,
            include_adversarial=payload.include_adversarial,
        )
    return result


@router.get("/runs")
def eval_runs():
    with get_conn() as conn:
        runs = conn.execute(
            """
            select r.*, m.provider, m.display_name as model_display_name
            from eval_runs r
            left join eval_models m on m.id=r.model_id
            where r.run_name is not null or r.aggregate_score is not null
            order by r.started_at desc nulls last, r.created_at desc
            limit 50
            """
        ).fetchall()
        items = conn.execute(
            """
            select i.*, q.category, q.expected_behavior
            from eval_run_items i
            left join eval_questions q on q.id=i.question_id
            where i.run_id in (select id from eval_runs order by created_at desc limit 50)
            order by i.id desc
            limit 200
            """
        ).fetchall()
    return {"runs": runs, "items": items}


@router.get("/runs/{run_id}")
def eval_run_detail(run_id: str):
    with get_conn() as conn:
        run = conn.execute("select * from eval_runs where id=%s", (run_id,)).fetchone()
        if not run:
            raise HTTPException(status_code=404, detail="Run not found")
        items = conn.execute(
            """
            select i.*, q.expected_behavior, q.tags_json
            from eval_run_items i
            left join eval_questions q on q.id=i.question_id
            where i.run_id=%s
            order by i.score asc nulls first
            """,
            (run_id,),
        ).fetchall()
    return {"run": run, "items": items}


@router.get("/runs/{run_id}/failures")
def eval_run_failures(run_id: str):
    with get_conn() as conn:
        return failures_payload(conn, run_id)


@router.get("/suites")
def eval_suites():
    with get_conn() as conn:
        return suites_payload(conn)


@router.get("/release-gate")
def eval_release_gate():
    with get_conn() as conn:
        return release_gate(conn)


@router.post("/refresh-external")
async def refresh_external(payload: RefreshExternalRequest | None = None):
    with get_conn() as conn:
        result = await refresh_external_scores(conn, provider=payload.provider if payload else None)
    return result


@router.get("/external-freshness")
def eval_external_freshness():
    with get_conn() as conn:
        return external_freshness(conn)


@router.post("/compare")
def compare(payload: CompareRequest | None = None):
    with get_conn() as conn:
        result = comparison_payload(conn, run_id=payload.run_id if payload else None)
        if result["run"] is None:
            return result
        conn.execute(
            "insert into eval_comparisons (run_id, comparison_payload_json) values (%s,%s::jsonb)",
            (result["run"]["id"], json.dumps(result, default=str)),
        )
    return result


@router.get("/compare")
def compare_latest():
    with get_conn() as conn:
        return comparison_payload(conn)


@router.get("/report")
def report(run_id: str | None = None):
    with get_conn() as conn:
        payload = report_payload(conn, run_id)
    if payload["run"] is None:
        raise HTTPException(status_code=404, detail="No eval report exists yet. Run /evals/run first.")
    return payload


@router.get("/report/latest.json")
def report_latest_json():
    with get_conn() as conn:
        payload = report_payload(conn)
    if payload["run"] is None:
        raise HTTPException(status_code=404, detail="No eval report exists yet. Run /evals/run first.")
    return payload


@router.get("/report/latest.md")
def report_latest_markdown():
    with get_conn() as conn:
        body = markdown_report(conn)
    return Response(content=body, media_type="text/markdown")


@router.get("/report/latest.csv")
def report_latest_csv():
    with get_conn() as conn:
        body = csv_report(conn)
    return Response(content=body, media_type="text/csv")


@router.post("/scholar-review/{run_item_id}")
def scholar_review(run_item_id: str, payload: ScholarReviewRequest):
    allowed = {"pending", "reviewed", "accepted", "rejected", "needs corpus update"}
    if payload.status not in allowed:
        raise HTTPException(status_code=400, detail="Invalid scholar review status.")
    with get_conn() as conn:
        row = conn.execute(
            """
            update eval_run_items
            set scholar_review_status=%s, scholar_review_note=%s, reviewed_at=now()
            where id=%s
            returning *
            """,
            (payload.status, payload.note, run_item_id),
        ).fetchone()
    if not row:
        raise HTTPException(status_code=404, detail="Run item not found.")
    return row
