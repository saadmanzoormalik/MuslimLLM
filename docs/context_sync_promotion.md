# Context Sync Promotion

Promotion is explicit, transactional, and idempotent. It requires a validation result of **Release candidate** or **Passed with exceptions**.

One PostgreSQL transaction locks the lab job, checks for a completed promotion, creates confirmed or explicitly accepted projects, creates chats and active-path messages, records provenance in `normalized_context_items`, and copies continuity packages. Any error rolls back the entire promotion.

Duplicate prevention uses the export SHA-256 plus provider source object IDs. Repeating **Promote to Muslim LLM** returns the existing result and creates no additional chats or projects. Existing Muslim LLM records are not updated or deleted.

Suggested projects are excluded unless the user has accepted them and promotion explicitly opts into suggestions.
