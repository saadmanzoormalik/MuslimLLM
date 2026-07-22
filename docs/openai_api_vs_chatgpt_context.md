# OpenAI API vs ChatGPT Context

These capabilities are deliberately separate:

| Capability | Current support |
|---|---|
| OpenAI API credential and model test | **OpenAI API Test** |
| ChatGPT consumer identity | Not inferred from an API key |
| ChatGPT conversation history | Official data export import |
| ChatGPT Projects and files | Only when represented in the export |
| Future history OAuth | Adapter reserved; disabled |

An OpenAI API key does not grant access to consumer ChatGPT history. The API test sends one small generation request to the configured endpoint, stores only status, hostname, model, latency, and error class, and does not persist the submitted key.
