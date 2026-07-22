# Context Sync Privacy Data Flow

## Data Minimization

The cloud broker receives only provider ID, public device keys, anonymous installation metadata, callback URI, app version, and authorization state. It does not receive conversation bodies, prompts, project names, files, Muslim LLM profile data, or local database content.

```text
Provider content -> encrypted provider connection -> Muslim LLM device
                 (never routed through the authorization broker)

Official export -> native file picker -> temporary local parse -> local PostgreSQL
```

Provider tokens are transient at the broker, encrypted in the grant, and erased after a successful one-time exchange. On the device they are encrypted at rest and cleared on disconnect. Temporary export files are deleted after parsing; normalized records retain provenance hashes and source IDs for auditability and deduplication.

Imported content is scanned and treated as untrusted. The system stores validation reports, progress events, checkpoints, and counts so failures are visible without logging sensitive content.

Users can disconnect a provider, delete provider-imported chats/projects, and export a portable local archive. Production retention periods, tenant isolation, deletion SLAs, audit access, and regional storage requirements must be set by policy before multi-user deployment.
