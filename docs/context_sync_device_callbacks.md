# Context Sync Device Callbacks

## Development Flow

1. Muslim LLM generates or loads an Ed25519/X25519 device identity.
2. `POST /context-sync/connect/demo` registers only public device material and a callback URL.
3. The broker returns the provider authorization URL.
4. The provider redirects to `http://127.0.0.1:8100/v1/oauth/demo/callback`.
5. The broker exchanges the code and redirects a grant ID to `http://127.0.0.1:8000/context-sync/device-callback/demo`.
6. The Mac signs and exchanges the grant, decrypts it locally, retrieves context directly, and returns to `/context-sync?job=...`.

Accepted frontend return origins default to `http://127.0.0.1:3000` and `http://localhost:3000`, with the exact path `/context-sync`. Accepted device callbacks are exact loopback URLs in development. Configure production callbacks explicitly; do not use wildcard redirects.

Callback failures return a short UI error code. Tokens, authorization codes, PKCE verifiers, signatures, and encrypted envelopes are never placed in the frontend return URL.
