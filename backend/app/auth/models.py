from ..db import get_conn


DDL = """
alter table users alter column email drop not null;
alter table users alter column password_hash drop not null;
alter table users add column if not exists email_normalized text;
alter table users add column if not exists avatar_url text;
alter table users add column if not exists status text not null default 'active';
alter table users add column if not exists email_verified boolean not null default false;
alter table users add column if not exists updated_at timestamptz not null default now();
alter table users add column if not exists last_login_at timestamptz;
create unique index if not exists users_email_normalized_key on users(email_normalized) where email_normalized is not null;

create table if not exists guest_accounts (
  id uuid primary key default gen_random_uuid(),
  guest_token_hash text unique not null,
  device_id text not null,
  created_at timestamptz not null default now(),
  expires_at timestamptz,
  converted_user_id uuid references users(id) on delete set null,
  converted_at timestamptz
);

create table if not exists auth_identities (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references users(id) on delete cascade,
  provider text not null check (provider in ('apple','google','email')),
  provider_subject text not null,
  provider_email text,
  provider_email_verified boolean not null default false,
  created_at timestamptz not null default now(),
  last_used_at timestamptz not null default now(),
  unique(provider, provider_subject)
);

create table if not exists auth_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  guest_id uuid references guest_accounts(id) on delete cascade,
  session_token_hash text unique not null,
  refresh_token_hash text unique not null,
  previous_refresh_token_hash text,
  device_id text not null,
  user_agent text,
  platform text,
  ip_hash text,
  access_expires_at timestamptz not null,
  expires_at timestamptz not null,
  revoked_at timestamptz,
  created_at timestamptz not null default now(),
  last_seen_at timestamptz not null default now(),
  authenticated_at timestamptz not null default now(),
  constraint auth_sessions_one_subject check ((user_id is not null)::int + (guest_id is not null)::int = 1)
);
create index if not exists auth_sessions_user_idx on auth_sessions(user_id) where revoked_at is null;
create index if not exists auth_sessions_guest_idx on auth_sessions(guest_id) where revoked_at is null;

create table if not exists email_auth_codes (
  id uuid primary key default gen_random_uuid(),
  email_normalized text not null,
  code_hash text not null,
  purpose text not null,
  attempts int not null default 0,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);
create index if not exists email_auth_codes_lookup_idx on email_auth_codes(email_normalized, created_at desc);

create table if not exists onboarding_profiles (
  id uuid primary key default gen_random_uuid(),
  user_id uuid unique references users(id) on delete cascade,
  guest_id uuid unique references guest_accounts(id) on delete cascade,
  primary_use text,
  response_preference text,
  privacy_preference text,
  context_transfer_preference text,
  onboarding_version text not null default 'v1',
  completed boolean not null default false,
  completed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  constraint onboarding_one_subject check ((user_id is not null)::int + (guest_id is not null)::int = 1)
);

create table if not exists temporary_onboarding_sessions (
  id uuid primary key default gen_random_uuid(),
  token_hash text unique not null,
  device_id text not null,
  answers_json jsonb not null default '{}'::jsonb,
  current_step int not null default 0,
  completed boolean not null default false,
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists auth_transactions (
  id uuid primary key default gen_random_uuid(),
  provider text not null,
  state_hash text unique not null,
  nonce_hash text not null,
  nonce_ciphertext text not null,
  pkce_verifier_ciphertext text not null,
  onboarding_token_hash text,
  guest_id uuid references guest_accounts(id) on delete set null,
  linking_user_id uuid references users(id) on delete cascade,
  return_to text not null default '/',
  expires_at timestamptz not null,
  consumed_at timestamptz,
  created_at timestamptz not null default now()
);
alter table auth_transactions add column if not exists nonce_ciphertext text;
alter table auth_transactions add column if not exists linking_user_id uuid references users(id) on delete cascade;

create table if not exists auth_audit_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete set null,
  guest_id uuid references guest_accounts(id) on delete set null,
  event_type text not null,
  provider text,
  success boolean not null,
  error_code text,
  device_id text,
  ip_hash text,
  created_at timestamptz not null default now()
);

create table if not exists auth_rate_limits (
  bucket text primary key,
  hits int not null default 0,
  window_started_at timestamptz not null default now(),
  blocked_until timestamptz
);

alter table chats add column if not exists guest_id uuid references guest_accounts(id) on delete cascade;
alter table projects add column if not exists guest_id uuid references guest_accounts(id) on delete cascade;
create index if not exists chats_user_updated_idx on chats(user_id, updated_at desc);
create index if not exists chats_guest_updated_idx on chats(guest_id, updated_at desc);
create index if not exists projects_user_updated_idx on projects(user_id, updated_at desc);
create index if not exists projects_guest_updated_idx on projects(guest_id, updated_at desc);

create table if not exists user_settings (
  id uuid primary key default gen_random_uuid(),
  user_id uuid references users(id) on delete cascade,
  guest_id uuid references guest_accounts(id) on delete cascade,
  key text not null,
  value jsonb not null,
  updated_at timestamptz not null default now(),
  constraint user_settings_one_subject check ((user_id is not null)::int + (guest_id is not null)::int = 1)
);
create unique index if not exists user_settings_user_key on user_settings(user_id, key) where user_id is not null;
create unique index if not exists user_settings_guest_key on user_settings(guest_id, key) where guest_id is not null;
"""


def ensure_auth_ready() -> None:
    with get_conn() as conn:
        conn.execute(DDL)
