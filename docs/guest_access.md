# Guest Access

Guest entry is one tap. FastAPI creates a random guest secret, stores only its hash, establishes an HttpOnly session, and attaches onboarding answers. Chats, projects, settings, and local model use are scoped to the guest UUID.

The first local guest may claim pre-authentication workspace rows once, preserving upgrades from older Muslim LLM builds. A returning browser restores the same guest through its rotating session cookie.
