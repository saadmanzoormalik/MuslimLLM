import asyncio
from pathlib import Path

from .auth import ensure_auth_ready
from .context_sync.service import ensure_context_sync_ready
from .db import get_conn
from .evals.router import ensure_evals_ready
from .imports.router import ensure_imports_ready
from .seed import seed_data


def apply_schema() -> None:
    schema_path = Path("/app/postgres/init.sql")
    if not schema_path.exists():
        schema_path = Path(__file__).resolve().parents[2] / "postgres" / "init.sql"
    with get_conn() as conn:
        conn.execute(schema_path.read_text(encoding="utf-8"))

    ensure_auth_ready()
    ensure_evals_ready()
    ensure_imports_ready()
    ensure_context_sync_ready()
    with get_conn() as conn:
        conn.execute(
            """
            update settings
            set value=jsonb_set(value, '{model}', '"muslim-llm-core"'::jsonb, true), updated_at=now()
            where key='llm' and value->>'model' in ('gpt-4.1-mini', 'qwen2.5:1.5b', 'muslim-llm-local')
            """
        )
        conn.execute("alter table messages add column if not exists status text not null default 'completed'")
        conn.execute("alter table messages add column if not exists error_json jsonb not null default '{}'::jsonb")
        conn.execute("alter table messages add column if not exists request_id text")
        conn.execute("alter table messages add column if not exists reasoning_summary text")
        conn.execute("alter table messages add column if not exists reasoning_metadata_json jsonb not null default '{}'::jsonb")


async def migrate() -> None:
    apply_schema()
    with get_conn() as conn:
        count = conn.execute("select count(*) as count from documents").fetchone()["count"]
    if count == 0:
        await seed_data()


if __name__ == "__main__":
    asyncio.run(migrate())
