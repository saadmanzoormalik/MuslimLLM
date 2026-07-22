from psycopg import Connection


def init_context_sync_schema(conn: Connection) -> None:
    for statement in [
        "alter table chats add column if not exists imported_from_provider text",
        "alter table chats add column if not exists imported_at timestamptz",
        "alter table chats add column if not exists import_job_id uuid",
        "alter table chats add column if not exists import_metadata_json jsonb not null default '{}'::jsonb",
        "alter table messages add column if not exists import_job_id uuid",
        "alter table messages add column if not exists source_message_id text",
        "alter table messages add column if not exists source_timestamp timestamptz",
        "alter table messages add column if not exists import_order int",
        "alter table messages add column if not exists imported_untrusted boolean not null default false",
        "alter table projects add column if not exists imported_from_provider text",
        "alter table projects add column if not exists imported_at timestamptz",
        "alter table projects add column if not exists import_job_id uuid",
        "alter table projects add column if not exists import_inferred boolean not null default false",
        "alter table projects add column if not exists import_metadata_json jsonb not null default '{}'::jsonb",
    ]:
        conn.execute(statement)

    conn.execute(
        """
        create table if not exists provider_connections (
          id uuid primary key default gen_random_uuid(),
          provider_id text not null,
          display_name text,
          auth_method text not null default 'official_export',
          status text not null default 'connected',
          source_account_hash text,
          scopes_json jsonb not null default '[]'::jsonb,
          encrypted_token_json jsonb not null default '{}'::jsonb,
          automatic_sync_enabled boolean not null default false,
          incremental_sync_enabled boolean not null default false,
          keep_provider_connected boolean not null default false,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          disconnected_at timestamptz
        )
        """
    )
    for statement in [
        "alter table provider_connections add column if not exists oauth_state_hash text",
        "alter table provider_connections add column if not exists encrypted_oauth_state_json jsonb not null default '{}'::jsonb",
        "alter table provider_connections add column if not exists oidc_nonce_hash text",
        "alter table provider_connections add column if not exists oauth_redirect_uri text",
        "alter table provider_connections add column if not exists return_uri text",
        "alter table provider_connections add column if not exists state_expires_at timestamptz",
        "alter table provider_connections add column if not exists api_base text",
        "alter table provider_connections add column if not exists api_model text",
        "alter table provider_connections add column if not exists connection_metadata_json jsonb not null default '{}'::jsonb",
        "alter table provider_connections add column if not exists last_checked_at timestamptz",
        "alter table provider_connections add column if not exists broker_connection_id uuid",
    ]:
        conn.execute(statement)
    conn.execute("create unique index if not exists provider_connections_oauth_state_idx on provider_connections(oauth_state_hash) where oauth_state_hash is not null")
    conn.execute(
        """
        create table if not exists device_auth_transactions (
          id uuid primary key default gen_random_uuid(),
          provider_id text not null,
          local_connection_id uuid not null references provider_connections(id) on delete cascade,
          broker_connection_id uuid not null,
          device_state_hash text not null unique,
          return_uri text not null,
          status text not null default 'authorizing',
          expires_at timestamptz not null,
          created_at timestamptz not null default now(),
          used_at timestamptz
        )
        """
    )
    conn.execute(
        """
        create table if not exists sync_jobs (
          id uuid primary key default gen_random_uuid(),
          provider_id text not null,
          connection_id uuid references provider_connections(id) on delete set null,
          status text not null default 'authorized',
          stage text not null default 'authorized',
          processed int not null default 0,
          total int not null default 0,
          percent numeric not null default 0,
          estimated_seconds_remaining int,
          inventory_json jsonb not null default '{}'::jsonb,
          options_json jsonb not null default '{}'::jsonb,
          upload_payload_json jsonb not null default '{}'::jsonb,
          correlation_id text not null default gen_random_uuid()::text,
          started_at timestamptz,
          completed_at timestamptz,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          last_error text
        )
        """
    )
    for statement in [
        "alter table sync_jobs add column if not exists display_message text not null default 'Securely connecting'",
        "alter table sync_jobs add column if not exists ready_for_use boolean not null default false",
        "alter table sync_jobs add column if not exists entry_chat_id uuid references chats(id) on delete set null",
        "alter table sync_jobs add column if not exists transfer_method text",
        "alter table sync_jobs add column if not exists provider_cursor text",
        "alter table sync_jobs add column if not exists archive_path_reference text",
        "alter table sync_jobs add column if not exists archive_hash text",
        "alter table sync_jobs add column if not exists items_discovered int not null default 0",
        "alter table sync_jobs add column if not exists items_processed int not null default 0",
        "alter table sync_jobs add column if not exists bytes_discovered bigint not null default 0",
        "alter table sync_jobs add column if not exists bytes_processed bigint not null default 0",
        "alter table sync_jobs add column if not exists checkpoint_json jsonb not null default '{}'::jsonb",
        "alter table sync_jobs add column if not exists last_processed_object text",
        "alter table sync_jobs add column if not exists last_error_code text",
        "alter table sync_jobs add column if not exists error_count int not null default 0",
        "alter table sync_jobs add column if not exists retry_count int not null default 0",
    ]:
        conn.execute(statement)
    conn.execute(
        """
        create table if not exists context_sync_uploads (
          id uuid primary key default gen_random_uuid(),
          provider_id text not null,
          connection_id uuid references provider_connections(id) on delete cascade,
          file_name text,
          inventory_json jsonb not null default '{}'::jsonb,
          payload_json jsonb not null default '{}'::jsonb,
          content_hash text,
          status text not null default 'ready',
          created_at timestamptz not null default now(),
          consumed_at timestamptz
        )
        """
    )
    for statement in [
        "alter table context_sync_uploads add column if not exists byte_size bigint not null default 0",
        "alter table context_sync_uploads add column if not exists archive_path_reference text",
    ]:
        conn.execute(statement)
    conn.execute(
        """
        create table if not exists sync_job_events (
          id uuid primary key default gen_random_uuid(),
          job_id uuid not null references sync_jobs(id) on delete cascade,
          stage text not null,
          status text not null,
          processed int not null default 0,
          total int not null default 0,
          percent numeric not null default 0,
          estimated_seconds_remaining int,
          message text,
          created_at timestamptz not null default now()
        )
        """
    )
    conn.execute(
        """
        create table if not exists sync_checkpoints (
          id uuid primary key default gen_random_uuid(),
          job_id uuid not null references sync_jobs(id) on delete cascade,
          stage text not null,
          cursor text,
          processed int not null default 0,
          checkpoint_json jsonb not null default '{}'::jsonb,
          created_at timestamptz not null default now()
        )
        """
    )
    conn.execute(
        """
        create table if not exists continuity_packages (
          id uuid primary key default gen_random_uuid(),
          job_id uuid references sync_jobs(id) on delete cascade,
          local_chat_id uuid references chats(id) on delete cascade,
          source_provider text not null,
          source_conversation_id text,
          package_json jsonb not null,
          confidence numeric not null default 0.7,
          created_at timestamptz not null default now(),
          unique(source_provider, source_conversation_id)
        )
        """
    )
    conn.execute(
        """
        create table if not exists continuity_validation_results (
          id uuid primary key default gen_random_uuid(),
          job_id uuid not null references sync_jobs(id) on delete cascade,
          local_chat_id uuid not null references chats(id) on delete cascade,
          source_conversation_id text,
          test_prompt text not null,
          objective_found boolean not null default false,
          decisions_found boolean not null default false,
          unresolved_tasks_found boolean not null default false,
          entities_found boolean not null default false,
          transcript_retrievable boolean not null default false,
          continuation_ready boolean not null default false,
          details_json jsonb not null default '{}'::jsonb,
          created_at timestamptz not null default now(),
          unique(job_id, local_chat_id)
        )
        """
    )
    conn.execute(
        """
        create table if not exists sync_exceptions (
          id uuid primary key default gen_random_uuid(),
          job_id uuid not null references sync_jobs(id) on delete cascade,
          provider_id text not null,
          item_type text,
          source_object_id text,
          user_message text not null,
          error_class text,
          recoverable boolean not null default true,
          created_at timestamptz not null default now()
        )
        """
    )
    conn.execute(
        """
        create table if not exists sync_audit_log (
          id uuid primary key default gen_random_uuid(),
          job_id uuid references sync_jobs(id) on delete cascade,
          provider_id text,
          event_type text not null,
          details_json jsonb not null default '{}'::jsonb,
          correlation_id text,
          created_at timestamptz not null default now()
        )
        """
    )
    conn.execute(
        """
        create table if not exists sync_validation_reports (
          id uuid primary key default gen_random_uuid(),
          provider_id text not null,
          connection_id uuid,
          job_id uuid not null references sync_jobs(id) on delete cascade,
          report_json jsonb not null,
          validation_status text not null,
          created_at timestamptz not null default now(),
          unique(job_id)
        )
        """
    )
    conn.execute(
        """
        create table if not exists normalized_context_items (
          id uuid primary key default gen_random_uuid(),
          job_id uuid references sync_jobs(id) on delete cascade,
          provider_id text not null,
          source_account_id_hash text,
          source_object_type text not null,
          source_object_id text not null,
          local_object_type text,
          local_object_id uuid,
          source_created_at timestamptz,
          source_updated_at timestamptz,
          imported_at timestamptz not null default now(),
          last_synced_at timestamptz not null default now(),
          raw_metadata_json jsonb not null default '{}'::jsonb,
          normalization_version text not null default 'context_sync_v1',
          parser_version text not null default 'generic_export_v1',
          content_hash text,
          parent_relationship_json jsonb not null default '{}'::jsonb,
          relationship_inferred boolean not null default false,
          unique(provider_id, source_account_id_hash, source_object_type, source_object_id)
        )
        """
    )
    conn.execute(
        """
        create table if not exists openai_export_archives (
          id uuid primary key default gen_random_uuid(),
          job_id uuid not null unique references sync_jobs(id) on delete cascade,
          archive_hash text not null,
          file_name text,
          file_count int not null default 0,
          decompressed_bytes bigint not null default 0,
          parser_version text not null,
          integrity_status text not null default 'validated',
          imported_at timestamptz not null default now()
        )
        """
    )
    conn.execute("create index if not exists openai_export_archives_hash_idx on openai_export_archives(archive_hash)")
    conn.execute(
        """
        create table if not exists openai_raw_conversations (
          id uuid primary key default gen_random_uuid(),
          job_id uuid not null references sync_jobs(id) on delete cascade,
          source_conversation_id text not null,
          source_content_hash text,
          archive_hash text not null,
          parser_version text not null,
          normalization_version text not null default 'context_sync_v1',
          raw_json jsonb not null,
          imported_at timestamptz not null default now(),
          unique(job_id, source_conversation_id)
        )
        """
    )
    conn.execute(
        """
        create table if not exists openai_raw_message_nodes (
          id uuid primary key default gen_random_uuid(),
          job_id uuid not null references sync_jobs(id) on delete cascade,
          source_conversation_id text not null,
          source_message_id text,
          source_node_id text not null,
          source_parent_id text,
          child_node_ids_json jsonb not null default '[]'::jsonb,
          role text,
          raw_content text,
          normalized_content text,
          source_timestamp timestamptz,
          source_content_hash text,
          source_model_metadata_json jsonb not null default '{}'::jsonb,
          source_metadata_json jsonb not null default '{}'::jsonb,
          archive_hash text not null,
          parser_version text not null,
          normalization_version text not null default 'context_sync_v1',
          is_active_branch boolean not null default false,
          is_orphan boolean not null default false,
          is_untrusted_instruction boolean not null default false,
          imported_at timestamptz not null default now(),
          unique(job_id, source_conversation_id, source_node_id)
        )
        """
    )
    conn.execute(
        """
        create table if not exists openai_conversation_branches (
          id uuid primary key default gen_random_uuid(),
          job_id uuid not null references sync_jobs(id) on delete cascade,
          source_conversation_id text not null,
          parent_node_id text not null,
          child_node_id text not null,
          is_active_branch boolean not null default false,
          archive_hash text not null,
          parser_version text not null,
          imported_at timestamptz not null default now(),
          unique(job_id, source_conversation_id, parent_node_id, child_node_id)
        )
        """
    )
    conn.execute(
        """
        create table if not exists openai_export_folder_watches (
          id uuid primary key default gen_random_uuid(),
          folder_path text not null,
          folder_name text not null,
          status text not null default 'watching',
          matched_file_name text,
          last_archive_hash text,
          seen_archive_hashes_json jsonb not null default '[]'::jsonb,
          job_id uuid references sync_jobs(id) on delete set null,
          last_error_code text,
          authorized_at timestamptz not null default now(),
          last_checked_at timestamptz,
          revoked_at timestamptz,
          updated_at timestamptz not null default now()
        )
        """
    )
    conn.execute("create index if not exists openai_export_folder_watches_active_idx on openai_export_folder_watches(status) where revoked_at is null")
    conn.execute(
        """
        create table if not exists context_transfer_consents (
          id uuid primary key default gen_random_uuid(),
          provider text not null,
          purpose text not null,
          consent_version text not null,
          privacy_notice_version text not null,
          accepted_at timestamptz not null default now(),
          data_categories_json jsonb not null default '[]'::jsonb,
          local_cloud_mode text not null default 'local',
          revoked_at timestamptz,
          receipt_hash text not null unique
        )
        """
    )
    conn.execute(
        """
        create table if not exists context_transfer_sessions (
          id uuid primary key default gen_random_uuid(),
          provider text not null default 'chatgpt',
          consent_id uuid not null references context_transfer_consents(id) on delete restrict,
          device_id_hash text not null,
          state text not null default 'consented',
          acquisition_method text,
          sync_job_id uuid references sync_jobs(id) on delete set null,
          folder_watch_id uuid references openai_export_folder_watches(id) on delete set null,
          ready_for_use boolean not null default false,
          background_sync_continues boolean not null default false,
          last_error_code text,
          retry_count int not null default 0,
          created_at timestamptz not null default now(),
          updated_at timestamptz not null default now(),
          completed_at timestamptz,
          cancelled_at timestamptz
        )
        """
    )
    conn.execute("create index if not exists context_transfer_sessions_state_idx on context_transfer_sessions(state,updated_at desc)")
    for statement in [
        "alter table context_transfer_sessions add column if not exists granted_capabilities_json jsonb not null default '[]'::jsonb",
        "alter table context_transfer_sessions add column if not exists transfer_method text",
    ]:
        conn.execute(statement)
    conn.execute(
        """
        create table if not exists context_transfer_session_events (
          id uuid primary key default gen_random_uuid(),
          session_id uuid not null references context_transfer_sessions(id) on delete cascade,
          from_state text,
          to_state text not null,
          event_type text not null default 'state_transition',
          details_json jsonb not null default '{}'::jsonb,
          created_at timestamptz not null default now()
        )
        """
    )
    conn.execute("create index if not exists context_transfer_session_events_idx on context_transfer_session_events(session_id,created_at)")
    conn.execute(
        """
        create table if not exists context_transfer_permissions (
          id uuid primary key default gen_random_uuid(),
          provider text not null,
          permission_type text not null,
          status text not null default 'active',
          grant_reference_id uuid,
          granted_at timestamptz not null default now(),
          expires_at timestamptz,
          revoked_at timestamptz,
          metadata_json jsonb not null default '{}'::jsonb
        )
        """
    )
    conn.execute("create index if not exists context_transfer_permissions_active_idx on context_transfer_permissions(provider,permission_type,status)")
    compatibility_views = {
        "context_sync_connections": "select * from provider_connections",
        "context_sync_jobs": "select * from sync_jobs",
        "context_sync_job_events": "select * from sync_job_events",
        "context_sync_checkpoints": "select * from sync_checkpoints",
        "context_sync_exceptions": "select * from sync_exceptions",
        "context_sync_audit_log": "select * from sync_audit_log",
        "imported_conversations": "select * from chats where imported_from_provider is not null",
        "imported_messages": "select message.* from messages message join chats chat on chat.id=message.chat_id where chat.imported_from_provider is not null",
        "imported_projects": "select * from projects where imported_from_provider is not null",
        "imported_files": "select * from normalized_context_items where source_object_type='file'",
    }
    for view_name, query in compatibility_views.items():
        exists = conn.execute("select to_regclass(%s) as relation", (f"public.{view_name}",)).fetchone()["relation"]
        if not exists:
            conn.execute(f"create view {view_name} as {query}")
