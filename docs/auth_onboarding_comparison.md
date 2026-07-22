# Auth and Onboarding Comparison

| Capability | Muslim LLM implementation | Target pattern |
|---|---|---|
| Required onboarding | 3 tap-to-advance questions | At most 3 |
| First screen to auth | 3 taps | At most 3 |
| Guest entry | 1 tap | 1 tap |
| Email | Address + 6-digit code | Passwordless |
| Google / Apple | OIDC Code + PKCE | Provider-controlled approval |
| Session | HttpOnly access + rotating refresh | Persistent, revocable |
| Mobile | Touch targets, single column, no sidebar | One purpose per screen |
| Accessibility | headings, radio semantics, labels, focus rings | Keyboard and screen-reader ready |
| Error recovery | visible message and one retry path | No blank callback |
| Guest conversion | transactional with stable IDs | No lost workspace data |

This matches common AI-assistant usability patterns without copying proprietary branding or assets.
