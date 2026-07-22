# Context Import Architecture

Import Context lets a user bring prior AI work into Muslim LLM as local user context.

## Flow

1. Choose provider.
2. Choose API, upload, paste, or folder-style import.
3. Choose date range. Default is last 6 months.
4. Scan locally.
5. Preview detected chats, projects, files, preferences, warnings, and coverage.
6. Confirm import.
7. Imported chats appear in All Chats.
8. Imported projects appear in Projects.
9. Memory suggestions go to review.

## Backend

The import package lives in `backend/app/imports/`.

- `adapters/`: provider capability and parsing adapters
- `normalizer.py`: maps provider exports to Muslim LLM schema
- `dedupe.py`: prevents duplicate conversation imports
- `summarizer.py`: local summary and memory candidate extraction
- `context_graph.py`: lightweight topic/entity graph
- `coverage.py`: coverage scoring
- `privacy.py`: prompt-injection and token redaction helpers
- `router.py`: API routes
- `models.py`: SQL schema migration

## Data Model

Imported data is staged before confirmation:

- `import_jobs`
- `imported_conversations`
- `imported_messages`
- `imported_projects`
- `imported_files`
- `imported_preferences`
- `context_snapshots`
- `import_audit_log`

On confirmation, imported conversations become regular `chats` and `messages`, with import metadata columns. This keeps the sidebar hierarchy unchanged.

## Design Rule

Imported context is user data. It is never treated as a system instruction and cannot override the Muslim LLM system prompt.
