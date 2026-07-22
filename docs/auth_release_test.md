# Authentication Release Test

## Local release path

1. Open `http://127.0.0.1:3000/` in a fresh browser profile.
2. Answer the three onboarding questions; refresh after question two and verify it resumes there.
3. Choose guest, create a chat and project, refresh, and verify both remain.
4. Open Settings, choose Connect account, enter an email, use the local inbox code, and verify the guest workspace remains.
5. Sign out, repeat the email-code flow, and verify the same account opens.
6. Sign out all devices and verify old sessions fail.
7. Delete an isolated test account and wait for backend completion.

## Provider release path

Configure Google and Apple from their setup documents. For each provider test signup, returning sign-in, cancel, stale state, wrong nonce, wrong issuer/audience contract tests, callback retry, and private relay behavior for Apple. Mock OIDC is CI-only; release validation must use configured providers.

## Failure and device checks

Test an expired email code, sixth wrong attempt, resend cooldown, offline callback, revoked refresh token, refresh replay, 390x844 mobile viewport, keyboard-only completion, visible focus, and screen-reader labels. `/auth-diagnostics` must show configuration status without secrets.

Release is ready only when there are no blank states, silent failures, plaintext credentials, token storage in localStorage, duplicate provider identities, lost guest data, or broken mobile layouts.
