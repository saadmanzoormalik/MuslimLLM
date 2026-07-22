# Context Authorization Broker

Authorization-only service for Muslim LLM Context Sync. It owns OAuth state, PKCE token exchange, one-time device-bound grants, revocation, rate limiting, and audit events. Conversation content is not accepted or stored.

The development broker enables only `Demo AI Account`. Production refuses the development encryption key and must disable the mock provider.
