from .base import OIDCProvider

APPLE = OIDCProvider(
    name="apple",
    issuer="https://appleid.apple.com",
    authorize_url="https://appleid.apple.com/auth/authorize",
    token_url="https://appleid.apple.com/auth/token",
    jwks_url="https://appleid.apple.com/auth/keys",
    client_id_env="APPLE_CLIENT_ID",
    client_secret_env=None,
    redirect_uri_env="APPLE_REDIRECT_URI",
)
