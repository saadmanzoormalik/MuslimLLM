# Context Sync Provider Limitations

Capabilities are recorded in `backend/app/context_sync/provider_capabilities.yaml` and enforced separately from model API credentials.

| Provider | Current consumer-history method | Direct history claim |
|---|---|---|
| Demo AI Account | Development broker OAuth and mock API | Yes, development only |
| ChatGPT | Official export ZIP/JSON | No |
| Claude | Official export when supplied | No |
| Gemini | Official export/Takeout when supplied | No |
| DeepSeek, Grok, Qwen, GLM | Official/generic export when supplied | No |
| Copilot, Perplexity | Unavailable or limited pending a verified route | No |

An OpenAI-compatible model key can generate new answers; it does not authorize access to a consumer assistant's chat history. OAuth availability also does not imply a consumer-history API. Missing projects, branches, artifacts, memory, or files are reported as unavailable rather than inferred as complete.

Run `backend/.venv/bin/python backend/app/context_sync/verify_provider_capabilities.py` while local services are running to verify the Demo connector. Commercial providers are never promoted to direct sync without an official capability and test evidence.
