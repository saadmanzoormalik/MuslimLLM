# Apple Authentication Setup

1. Create a Services ID and enable Sign in with Apple.
2. Register the exact HTTPS return URL ending in `/auth/apple/callback`.
3. Download the Apple signing key and store it outside the repository.
4. Set `APPLE_CLIENT_ID`, `APPLE_TEAM_ID`, `APPLE_KEY_ID`, `APPLE_PRIVATE_KEY_PATH`, and `APPLE_REDIRECT_URI`.
5. Restart FastAPI and test first-login name capture, later login without a name, private relay email, cancellation, and revoked access.

The private key and generated Apple client secret never enter frontend code or logs.
