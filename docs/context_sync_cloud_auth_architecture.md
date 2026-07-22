# Context Sync Cloud Authorization Architecture

## Decision

The broker decides only whether a verified device may receive a short-lived provider credential. It never retrieves or stores conversation content. The Mac decides what content to retrieve, normalize, and retain.

```text
Muslim LLM on Mac
  -> Context Authorization Broker
  -> provider authorization page
  -> broker callback and PKCE token exchange
  -> one-time device-bound grant
  -> encrypted token delivered to the Mac
  -> Mac retrieves provider context directly
  -> local PostgreSQL normalization and continuity packages
```

Services:

- `services/context-auth-broker`: state, PKCE, provider token exchange, grant issuance, revocation, and security audit events.
- `services/mock-context-provider`: development-only provider used to prove the complete protocol.
- `backend/app/context_sync`: device identity, grant decryption, direct retrieval, durable jobs, deduplication, and validation.
- `frontend/app/context-sync`: two-step provider selection and consent, progress, completion, and continuation.

The broker database contains connection metadata, hashed state, encrypted transactions, one-time grants, and redacted audit events. It does not accept chat bodies, files, prompts, project names, or local database content.

Production deploys the broker on HTTPS with a managed PostgreSQL database and a secret-manager supplied encryption key. The mock provider and `demo` capability are disabled when `APP_ENVIRONMENT=production`.
