# Provider Import Capabilities

Muslim LLM does not claim unsupported provider access.

## Current MVP

| Provider | One-click API | Upload Export | Projects | Attachments | Memories |
|---|---:|---:|---:|---:|---:|
| ChatGPT | No | Yes | If present | If present | If present |
| Claude | No | Yes | If present | If present | No |
| Gemini | No | Yes | If present | If present | No |
| DeepSeek | No | Generic | No | No | No |
| Grok | No | Generic | No | No | No |
| Qwen | No | Generic | No | No | No |
| GLM | No | Generic | No | No | No |
| Generic JSON | No | Yes | Yes | If present | If present |
| Generic Markdown | No | Yes | Inferred | No | No |

## Fallback Message

When full API import is unavailable, the adapter returns:

```json
{
  "supported": false,
  "reason": "Provider does not expose full chat export API. Use uploaded export file instead."
}
```

## Supported Upload Formats

- `.json`
- `.jsonl` where provider parser supports it later
- `.zip` for ChatGPT-style exports containing `conversations.json`
- `.md`
- `.txt`
- `.csv`

Folder import is represented by generic JSON metadata in the MVP. Browser folder upload can be added later on the frontend.
