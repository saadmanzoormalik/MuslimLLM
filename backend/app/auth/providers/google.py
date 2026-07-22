from .base import OIDCProvider

GOOGLE = OIDCProvider(
    name="google",
    issuer="https://accounts.google.com",
    authorize_url="https://accounts.google.com/o/oauth2/v2/auth",
    token_url="https://oauth2.googleapis.com/token",
    jwks_url="https://www.googleapis.com/oauth2/v3/certs",
    client_id_env="GOOGLE_OAUTH_CLIENT_ID",
    client_secret_env="GOOGLE_OAUTH_CLIENT_SECRET",
    redirect_uri_env="GOOGLE_OAUTH_REDIRECT_URI",
)
