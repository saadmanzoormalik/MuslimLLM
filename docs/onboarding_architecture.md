# Onboarding Architecture

The decision being improved is the user's first choice of how Muslim LLM should help and protect their data. Three answers establish primary use, response depth, and privacy mode before account friction appears.

```text
First visit -> temporary HttpOnly onboarding token -> three saved answers
-> account choice -> durable user or guest -> main chat
```

`temporary_onboarding_sessions` restores the current step after refresh. Authentication atomically copies the answers into `onboarding_profiles` and consumes the temporary token. The optional ChatGPT transfer preference never blocks activation.

Frontend: `frontend/app/onboarding/page.tsx` and `frontend/components/onboarding/`.
Backend: `backend/app/auth/onboarding.py` and `/onboarding/*`.
