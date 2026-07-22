from psycopg import Connection


def init_import_schema(conn: Connection) -> None:
    for statement in [
        "alter table chats add column if not exists imported_from_provider text",
        "alter table chats add column if not exists imported_at timestamptz",
        "alter table chats add column if not exists import_job_id uuid",
        "alter table chats add column if not exists import_metadata_json jsonb not null default '{}'::jsonb",
        "alter table projects add column if not exists imported_from_provider text",
        "alter table projects add column if not exists imported_at timestamptz",
        "alter table projects add column if not exists import_job_id uuid",
        "alter table projects add column if not exists import_inferred boolean not null default false",
        "alter table projects add column if not exists import_metadata_json jsonb not null default '{}'::jsonb",
    ]:
        conn.execute(statement)

    conn.execute(
        """
        create table if not exists import_jobs (
          id uuid primary key default gen_random_uuid(),
          provider text not null,
          import_mode text not null check (import_mode in ('api','file','paste','folder')),
          status text not null check (status in ('pending','scanning','preview_ready','importing','completed','failed','cancelled')),
          selected_date_range_start timestamptz,
          selected_date_range_end timestamptz,
          total_items_detected int not null default 0,
          total_items_imported int not null default 0,
          total_items_skipped int not null default 0,
          coverage_score numeric,
          created_at timestamptz not null default now(),
          completed_at timestamptz,
          error_message text
        )
        """
    )
    conn.execute(
        """
        create table if not exists imported_conversations (
          id uuid primary key default gen_random_uuid(),
          import_job_id uuid not null references import_jobs(id) on delete cascade,
          source_provider text not null,
          source_conversation_id text,
          title text not null,
          created_at_source timestamptz,
          updated_at_source timestamptz,
          imported_chat_id uuid references chats(id) on delete set null,
          message_count int not null default 0,
          attachment_count int not null default 0,
          token_estimate int not null default 0,
          import_status text not null default 'pending',
          coverage_json jsonb not null default '{}'::jsonb,
          raw_metadata_json jsonb not null default '{}'::jsonb,
          unique(import_job_id, source_conversation_id)
        )
        """
    )
    conn.execute(
        """
        create table if not exists imported_messages (
          id uuid primary key default gen_random_uuid(),
          imported_conversation_id uuid not null references imported_conversations(id) on delete cascade,
          role text not null check (role in ('user','assistant','system','tool','unknown')),
          content text not null,
          created_at_source timestamptz,
          model_name_source text,
          attachments_json jsonb not null default '[]'::jsonb,
          citations_json jsonb not null default '[]'::jsonb,
          raw_metadata_json jsonb not null default '{}'::jsonb
        )
        """
    )
    conn.execute(
        """
        create table if not exists imported_projects (
          id uuid primary key default gen_random_uuid(),
          import_job_id uuid not null references import_jobs(id) on delete cascade,
          source_provider text not null,
          source_project_id text,
          title text not null,
          description text,
          imported_project_id uuid references projects(id) on delete set null,
          conversation_count int not null default 0,
          file_count int not null default 0,
          import_status text not null default 'pending',
          coverage_json jsonb not null default '{}'::jsonb,
          raw_metadata_json jsonb not null default '{}'::jsonb
        )
        """
    )
    conn.execute(
        """
        create table if not exists imported_files (
          id uuid primary key default gen_random_uuid(),
          import_job_id uuid not null references import_jobs(id) on delete cascade,
          source_provider text not null,
          source_file_id text,
          filename text not null,
          mime_type text,
          size_bytes int,
          local_document_id uuid references documents(id) on delete set null,
          linked_chat_id uuid references chats(id) on delete set null,
          linked_project_id uuid references projects(id) on delete set null,
          import_status text not null default 'pending',
          hash_sha256 text,
          raw_metadata_json jsonb not null default '{}'::jsonb
        )
        """
    )
    conn.execute(
        """
        create table if not exists imported_preferences (
          id uuid primary key default gen_random_uuid(),
          import_job_id uuid not null references import_jobs(id) on delete cascade,
          preference_type text not null check (preference_type in ('memory','custom_instruction','tone','domain_preference','identity','other')),
          content text not null,
          confidence_level text not null default 'medium',
          source_provider text not null,
          imported_into_profile boolean not null default false,
          requires_user_review boolean not null default true,
          review_status text not null default 'pending',
          raw_metadata_json jsonb not null default '{}'::jsonb
        )
        """
    )
    conn.execute(
        """
        create table if not exists context_snapshots (
          id uuid primary key default gen_random_uuid(),
          import_job_id uuid not null references import_jobs(id) on delete cascade,
          snapshot_type text not null check (snapshot_type in ('conversation_summary','project_summary','user_profile_summary','domain_memory','preference_summary')),
          title text not null,
          content text not null,
          confidence_level text not null default 'medium',
          source_refs_json jsonb not null default '[]'::jsonb,
          created_at timestamptz not null default now()
        )
        """
    )
    conn.execute(
        """
        create table if not exists import_audit_log (
          id uuid primary key default gen_random_uuid(),
          import_job_id uuid references import_jobs(id) on delete cascade,
          provider text,
          event_type text not null,
          details_json jsonb not null default '{}'::jsonb,
          created_at timestamptz not null default now()
        )
        """
    )
