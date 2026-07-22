# Import Privacy And Security

Import Context follows Muslim LLM's local-first privacy posture.

## Local By Default

- Uploaded exports are parsed locally.
- Summaries are generated with deterministic local logic in the MVP.
- Imported chats are not sent to cloud APIs.
- Cloud summarization is rejected unless explicitly implemented and enabled.

## Credential Handling

The MVP does not store provider credentials. `POST /imports/revoke/{provider}` records revocation and returns that no stored credentials exist.

## Prompt Injection Protection

Imported content is scanned for patterns such as:

- ignore previous instructions
- system prompt extraction
- exfiltration requests
- API key requests

Warnings appear in the preview/report. Imported provider system messages are stripped or downgraded before becoming Muslim LLM chat messages.

## Memory Review

Memory suggestions are not automatically applied. Users must accept or reject each suggestion.

## Audit Events

The audit log records:

- provider connection attempt
- import preview generated
- prompt-injection warnings
- import confirmed
- import completed
- import cancelled
- credentials deleted

Tokens and likely API keys are redacted before audit details are stored.
