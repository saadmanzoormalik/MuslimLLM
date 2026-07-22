create extension if not exists vector;
create extension if not exists pgcrypto;

create table if not exists users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  password_hash text not null,
  display_name text,
  created_at timestamptz not null default now()
);

create table if not exists chats (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  project_id uuid,
  title text not null default 'New chat',
  model text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists projects (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  name text not null,
  description text,
  color text not null default 'emerald',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table chats add column if not exists project_id uuid;

do $$
begin
  if not exists (
    select 1 from pg_constraint where conname = 'chats_project_id_fkey'
  ) then
    alter table chats
      add constraint chats_project_id_fkey foreign key (project_id) references projects(id) on delete set null;
  end if;
end $$;

create table if not exists messages (
  id uuid primary key default gen_random_uuid(),
  chat_id uuid not null references chats(id) on delete cascade,
  role text not null check (role in ('system', 'user', 'assistant')),
  content text not null,
  citations jsonb not null default '[]'::jsonb,
  model text,
  status text not null default 'completed',
  error_json jsonb not null default '{}'::jsonb,
  request_id text,
  reasoning_summary text,
  reasoning_metadata_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists documents (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  author text,
  source_type text not null default 'Other',
  madhab text not null default 'Unknown',
  period text not null default 'Unknown',
  geography text,
  language text not null default 'English',
  reference text,
  reliability_level text not null default 'Unknown',
  copyright_status text,
  uploaded_by text,
  file_name text,
  content text not null,
  created_at timestamptz not null default now()
);

create table if not exists document_chunks (
  id uuid primary key default gen_random_uuid(),
  document_id uuid not null references documents(id) on delete cascade,
  chunk_index int not null,
  content text not null,
  token_count int not null default 0,
  embedding vector(1536),
  created_at timestamptz not null default now()
);

create index if not exists document_chunks_embedding_idx
  on document_chunks using ivfflat (embedding vector_cosine_ops) with (lists = 100);

create table if not exists eval_questions (
  id uuid primary key default gen_random_uuid(),
  question text not null,
  ideal_answer text,
  source_expectation text,
  category text not null default 'General',
  created_at timestamptz not null default now()
);

create table if not exists eval_runs (
  id uuid primary key default gen_random_uuid(),
  eval_question_id uuid references eval_questions(id) on delete set null,
  answer text not null,
  citation_accuracy numeric not null default 0,
  hallucination_risk numeric not null default 0,
  islamic_nuance numeric not null default 0,
  madhab_awareness numeric not null default 0,
  historical_accuracy numeric not null default 0,
  general_usefulness numeric not null default 0,
  refusal_correctness numeric not null default 0,
  overall_score numeric not null default 0,
  notes text,
  created_at timestamptz not null default now()
);

create table if not exists settings (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now()
);

create table if not exists eval_models (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  model_name text not null,
  display_name text not null,
  model_family text,
  is_local boolean not null default false,
  api_base text,
  api_model_name text,
  is_active boolean not null default true,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(provider, model_name)
);

create table if not exists eval_benchmarks (
  id uuid primary key default gen_random_uuid(),
  name text not null unique,
  category text not null,
  description text,
  benchmark_type text not null check (benchmark_type in ('external_reported','internal_question_set','llm_judge','deterministic')),
  source_url text,
  source_name text,
  higher_is_better boolean not null default true,
  max_score numeric not null default 100,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists external_model_scores (
  id uuid primary key default gen_random_uuid(),
  model_id uuid not null references eval_models(id) on delete cascade,
  benchmark_id uuid not null references eval_benchmarks(id) on delete cascade,
  score numeric,
  score_unit text not null default 'points',
  source_url text,
  source_name text,
  confidence_level text not null check (confidence_level in ('high','medium','low')),
  fetched_at timestamptz not null default now(),
  manually_configured boolean not null default true,
  raw_payload_json jsonb not null default '{}'::jsonb
);

alter table external_model_scores add column if not exists model_version_or_date text;
alter table external_model_scores add column if not exists benchmark_category text;
alter table external_model_scores add column if not exists max_score numeric not null default 100;
alter table external_model_scores add column if not exists normalized_score_0_100 numeric;
alter table external_model_scores add column if not exists source_type text not null default 'Manual source';
alter table external_model_scores add column if not exists published_at timestamptz;
alter table external_model_scores add column if not exists notes text;
alter table external_model_scores add column if not exists freshness_status text not null default 'Unknown freshness';

create table if not exists eval_question_sets (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  description text,
  category text not null,
  version text not null default 'v1',
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(name, version)
);

alter table eval_questions add column if not exists question_set_id uuid references eval_question_sets(id) on delete set null;
alter table eval_questions add column if not exists expected_behavior text;
alter table eval_questions add column if not exists sub_category text;
alter table eval_questions add column if not exists difficulty text default 'medium';
alter table eval_questions add column if not exists risk_level text default 'medium';
alter table eval_questions add column if not exists scoring_method text default 'deterministic';
alter table eval_questions add column if not exists stable_id text;
alter table eval_questions add column if not exists tags_json jsonb not null default '[]'::jsonb;
alter table eval_questions add column if not exists scoring_rubric_json jsonb not null default '{}'::jsonb;
alter table eval_questions alter column ideal_answer drop not null;

alter table eval_runs alter column answer drop not null;
alter table eval_runs add column if not exists model_id uuid references eval_models(id) on delete set null;
alter table eval_runs add column if not exists run_name text;
alter table eval_runs add column if not exists status text not null default 'completed';
alter table eval_runs add column if not exists started_at timestamptz;
alter table eval_runs add column if not exists completed_at timestamptz;
alter table eval_runs add column if not exists total_questions int not null default 0;
alter table eval_runs add column if not exists aggregate_score numeric;
alter table eval_runs add column if not exists weighted_score numeric;
alter table eval_runs add column if not exists pass_rate numeric;
alter table eval_runs add column if not exists critical_failures_count int not null default 0;
alter table eval_runs add column if not exists hallucination_flags_count int not null default 0;
alter table eval_runs add column if not exists fabricated_religious_source_flags_count int not null default 0;
alter table eval_runs add column if not exists scholar_consultation_misses int not null default 0;
alter table eval_runs add column if not exists science_overframing_count int not null default 0;
alter table eval_runs add column if not exists average_latency_ms int;
alter table eval_runs add column if not exists failed_questions jsonb not null default '[]'::jsonb;
alter table eval_runs add column if not exists dimension_scores_json jsonb not null default '{}'::jsonb;
alter table eval_runs add column if not exists category_scores_json jsonb not null default '[]'::jsonb;
alter table eval_runs add column if not exists eval_set_version text not null default 'v1';
alter table eval_runs add column if not exists prompt_version text not null default 'muslim_llm_system_prompt_v1';
alter table eval_runs add column if not exists model_version text;
alter table eval_runs add column if not exists rag_corpus_version text not null default 'local_seed_v1';
alter table eval_runs add column if not exists alignment_rules_version text not null default 'alignment_rules_v1';
alter table eval_runs add column if not exists system_prompt_hash text;
alter table eval_runs add column if not exists alignment_rules_hash text;
alter table eval_runs add column if not exists rag_corpus_hash text;
alter table eval_runs add column if not exists eval_set_hash text;
alter table eval_runs add column if not exists temperature numeric not null default 0.2;
alter table eval_runs add column if not exists top_p numeric;
alter table eval_runs add column if not exists max_tokens int;
alter table eval_runs add column if not exists judge_model text;
alter table eval_runs add column if not exists judge_prompt_hash text;
alter table eval_runs add column if not exists judge_type text not null default 'deterministic';
alter table eval_runs add column if not exists confidence_level text not null default 'medium';

create table if not exists eval_run_items (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references eval_runs(id) on delete cascade,
  question_id uuid references eval_questions(id) on delete set null,
  prompt text not null,
  model_answer text,
  score numeric,
  score_json jsonb not null default '{}'::jsonb,
  judge_explanation text,
  latency_ms int,
  token_estimate int,
  error text
);

alter table eval_run_items add column if not exists category text;
alter table eval_run_items add column if not exists sub_category text;
alter table eval_run_items add column if not exists difficulty text;
alter table eval_run_items add column if not exists risk_level text;
alter table eval_run_items add column if not exists dimension_scores_json jsonb not null default '{}'::jsonb;
alter table eval_run_items add column if not exists critical_failure boolean not null default false;
alter table eval_run_items add column if not exists failure_type text;
alter table eval_run_items add column if not exists hallucination_flag boolean not null default false;
alter table eval_run_items add column if not exists fabricated_religious_source_flag boolean not null default false;
alter table eval_run_items add column if not exists scholar_consultation_miss boolean not null default false;
alter table eval_run_items add column if not exists science_overframing boolean not null default false;
alter table eval_run_items add column if not exists recommended_fix text;
alter table eval_run_items add column if not exists likely_fix_type text;
alter table eval_run_items add column if not exists scholar_review_status text not null default 'pending';
alter table eval_run_items add column if not exists scholar_review_note text;
alter table eval_run_items add column if not exists reviewed_at timestamptz;

create table if not exists eval_comparisons (
  id uuid primary key default gen_random_uuid(),
  run_id uuid references eval_runs(id) on delete cascade,
  comparison_payload_json jsonb not null,
  created_at timestamptz not null default now()
);

alter table chats add column if not exists imported_from_provider text;
alter table chats add column if not exists imported_at timestamptz;
alter table chats add column if not exists import_job_id uuid;
alter table chats add column if not exists import_metadata_json jsonb not null default '{}'::jsonb;
alter table projects add column if not exists imported_from_provider text;
alter table projects add column if not exists imported_at timestamptz;
alter table projects add column if not exists import_job_id uuid;
alter table projects add column if not exists import_inferred boolean not null default false;
alter table projects add column if not exists import_metadata_json jsonb not null default '{}'::jsonb;

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
);

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
);

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
);

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
);

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
);

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
);

create table if not exists context_snapshots (
  id uuid primary key default gen_random_uuid(),
  import_job_id uuid not null references import_jobs(id) on delete cascade,
  snapshot_type text not null check (snapshot_type in ('conversation_summary','project_summary','user_profile_summary','domain_memory','preference_summary')),
  title text not null,
  content text not null,
  confidence_level text not null default 'medium',
  source_refs_json jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now()
);

create table if not exists import_audit_log (
  id uuid primary key default gen_random_uuid(),
  import_job_id uuid references import_jobs(id) on delete cascade,
  provider text,
  event_type text not null,
  details_json jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

insert into settings (key, value) values
  ('llm', '{"model":"muslim-llm-core","temperature":0.3}'::jsonb),
  ('retrieval', '{"top_k":6,"islamic_threshold":0.35}'::jsonb),
  ('ui', '{"theme":"system"}'::jsonb)
on conflict (key) do nothing;
