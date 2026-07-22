# Google Authentication Setup

1. Create an OAuth 2.0 Web application in Google Cloud.
2. Register the exact callback `http://127.0.0.1:8000/auth/google/callback` for local use.
3. Set `GOOGLE_OAUTH_CLIENT_ID`, `GOOGLE_OAUTH_CLIENT_SECRET`, and `GOOGLE_OAUTH_REDIRECT_URI` in the backend environment.
4. Restart FastAPI and check `/auth-diagnostics`.
5. Test new signup, returning sign-in, cancellation, invalid state, and expiry.

Production must use HTTPS and an exact hosted callback. The client secret stays backend-only.
