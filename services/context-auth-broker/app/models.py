from .database import get_conn


def ensure_schema() -> None:
    with get_conn() as conn:
        conn.execute("create extension if not exists pgcrypto")
        conn.execute(
            """
            create table if not exists auth_broker_connections (
              id uuid primary key default gen_random_uuid(),
              provider_id text not null,
              status text not null default 'authorizing',
              oauth_state_hash text not null unique,
              encrypted_transaction_json jsonb not null,
              device_signing_public_key text not null,
              device_encryption_public_key text not null,
              device_callback_uri text not null,
              platform text not null,
              app_version text,
              requested_capability text not null,
              expires_at timestamptz not null,
              created_at timestamptz not null default now(),
              completed_at timestamptz,
              revoked_at timestamptz
            )
            """
        )
        conn.execute(
            """
            create table if not exists auth_broker_grants (
              id uuid primary key default gen_random_uuid(),
              connection_id uuid not null references auth_broker_connections(id) on delete cascade,
              provider_id text not null,
              status text not null default 'ready',
              encrypted_token_json jsonb not null,
              device_signing_public_key text not null,
              device_encryption_public_key text not null,
              expires_at timestamptz not null,
              created_at timestamptz not null default now(),
              used_at timestamptz
            )
            """
        )
        conn.execute(
            """
            create table if not exists auth_broker_audit_log (
              id uuid primary key default gen_random_uuid(),
              connection_id uuid,
              grant_id uuid,
              provider_id text,
              event_type text not null,
              outcome text not null,
              details_json jsonb not null default '{}'::jsonb,
              created_at timestamptz not null default now()
            )
            """
        )
