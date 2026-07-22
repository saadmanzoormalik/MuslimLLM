from psycopg import Connection

from .config import schema_name


def init_lab_schema(conn: Connection) -> None:
    s = schema_name()
    conn.execute(f"create schema if not exists {s}")
    statements = [
        f"""create table if not exists {s}.lab_jobs (
          id uuid primary key default gen_random_uuid(), provider text not null default 'openai',
          status text not null default 'queued', stage text not null default 'queued', progress numeric not null default 0,
          source_filename text, source_hash text, parser_version text, storage_path text,
          inventory_json jsonb not null default '{{}}'::jsonb, counts_json jsonb not null default '{{}}'::jsonb,
          estimated_seconds_remaining int, retry_count int not null default 0, cancel_requested boolean not null default false,
          last_error text, created_at timestamptz not null default now(), updated_at timestamptz not null default now(), completed_at timestamptz
        )""",
        f"create unique index if not exists lab_jobs_source_hash_idx on {s}.lab_jobs(source_hash) where source_hash is not null",
        f"""create table if not exists {s}.lab_job_events (
          id bigserial primary key, job_id uuid not null references {s}.lab_jobs(id) on delete cascade,
          stage text not null, status text not null, message text not null, progress numeric not null default 0,
          details_json jsonb not null default '{{}}'::jsonb, created_at timestamptz not null default now()
        )""",
        f"""create table if not exists {s}.lab_checkpoints (
          id bigserial primary key, job_id uuid not null references {s}.lab_jobs(id) on delete cascade,
          stage text not null, cursor text, checkpoint_json jsonb not null default '{{}}'::jsonb,
          created_at timestamptz not null default now(), unique(job_id, stage)
        )""",
        f"""create table if not exists {s}.raw_openai_conversations (
          id uuid primary key default gen_random_uuid(), job_id uuid not null references {s}.lab_jobs(id) on delete cascade,
          source_conversation_id text not null, raw_json jsonb not null, content_hash text not null,
          parser_version text not null, created_at timestamptz not null default now(), unique(job_id, source_conversation_id)
        )""",
        f"""create table if not exists {s}.normalized_openai_conversations (
          id uuid primary key default gen_random_uuid(), job_id uuid not null references {s}.lab_jobs(id) on delete cascade,
          source_conversation_id text not null, title text not null, source_created_at timestamptz, source_updated_at timestamptz,
          current_node_id text, message_count int not null default 0, node_count int not null default 0, branch_count int not null default 0,
          project_source_id text, project_title text, project_status text not null default 'unassigned',
          content_hash text not null, parser_version text not null, metadata_json jsonb not null default '{{}}'::jsonb,
          created_at timestamptz not null default now(), unique(job_id, source_conversation_id)
        )""",
        f"""create table if not exists {s}.openai_message_nodes (
          id uuid primary key default gen_random_uuid(), job_id uuid not null references {s}.lab_jobs(id) on delete cascade,
          conversation_id uuid not null references {s}.normalized_openai_conversations(id) on delete cascade,
          source_conversation_id text not null, source_message_id text not null, source_node_id text not null, parent_id text,
          children_json jsonb not null default '[]'::jsonb, role text not null, content text not null default '', source_timestamp timestamptz,
          model_metadata_json jsonb not null default '{{}}'::jsonb, content_hash text not null, parser_version text not null,
          is_active boolean not null default false, is_orphan boolean not null default false, is_untrusted_instruction boolean not null default false,
          security_scan_json jsonb not null default '{{}}'::jsonb, raw_metadata_json jsonb not null default '{{}}'::jsonb,
          unique(job_id, source_conversation_id, source_node_id)
        )""",
        f"""create table if not exists {s}.openai_conversation_branches (
          id uuid primary key default gen_random_uuid(), job_id uuid not null references {s}.lab_jobs(id) on delete cascade,
          source_conversation_id text not null, parent_node_id text not null, child_node_id text not null,
          is_active_branch boolean not null default false, unique(job_id, source_conversation_id, parent_node_id, child_node_id)
        )""",
        f"""create table if not exists {s}.openai_export_files (
          id uuid primary key default gen_random_uuid(), job_id uuid not null references {s}.lab_jobs(id) on delete cascade,
          source_path text not null, filename text not null, size_bytes bigint not null, mime_type text,
          content_hash text not null, scan_status text not null, metadata_json jsonb not null default '{{}}'::jsonb,
          unique(job_id, source_path)
        )""",
        f"""create table if not exists {s}.openai_import_exceptions (
          id uuid primary key default gen_random_uuid(), job_id uuid not null references {s}.lab_jobs(id) on delete cascade,
          kind text not null, source_id text, message text not null, recoverable boolean not null default true,
          created_at timestamptz not null default now()
        )""",
        f"""create table if not exists {s}.lab_projects (
          id uuid primary key default gen_random_uuid(), job_id uuid not null references {s}.lab_jobs(id) on delete cascade,
          source_project_id text, title text not null, description text, status text not null,
          accepted boolean not null default false, metadata_json jsonb not null default '{{}}'::jsonb,
          unique(job_id, source_project_id)
        )""",
        f"""create table if not exists {s}.lab_continuity_packages (
          id uuid primary key default gen_random_uuid(), job_id uuid not null references {s}.lab_jobs(id) on delete cascade,
          source_conversation_id text not null, package_json jsonb not null, confidence numeric not null default 0,
          unique(job_id, source_conversation_id)
        )""",
        f"""create table if not exists {s}.lab_validation_reports (
          id uuid primary key default gen_random_uuid(), job_id uuid not null references {s}.lab_jobs(id) on delete cascade unique,
          status text not null, score numeric not null, report_json jsonb not null, created_at timestamptz not null default now()
        )""",
        f"""create table if not exists {s}.lab_promotions (
          id uuid primary key default gen_random_uuid(), job_id uuid not null references {s}.lab_jobs(id) on delete cascade unique,
          status text not null, result_json jsonb not null default '{{}}'::jsonb, created_at timestamptz not null default now(), completed_at timestamptz
        )""",
        f"""create table if not exists {s}.lab_api_tests (
          id uuid primary key default gen_random_uuid(), status text not null, api_base_host text, model text,
          latency_ms int, error_class text, created_at timestamptz not null default now()
        )""",
    ]
    for statement in statements:
        conn.execute(statement)
