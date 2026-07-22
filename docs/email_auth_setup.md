# Email Authentication Setup

The local environment uses `AUTH_EMAIL_PROVIDER=local`. A development-only mailbox endpoint supports end-to-end testing without logging codes. Production should replace `_deliver` in `backend/app/auth/email_codes.py` with a transactional-email adapter.

Codes are six digits, cryptographically random, HMAC-hashed in PostgreSQL, single-use, valid for ten minutes, and limited to five attempts. Resending consumes older codes. Per-email and per-IP buckets limit abuse without revealing whether an account exists.
