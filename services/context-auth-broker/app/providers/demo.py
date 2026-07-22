from urllib.parse import urlencode

from ..config import settings
from .base import ProviderDefinition


definition = ProviderDefinition("demo", "Demo AI Account", "oauth", settings.environment == "development" and settings.allow_mock_provider, True, False)


def authorization_url(state: str, challenge: str, redirect_uri: str) -> str:
    return f"{settings.mock_provider_url}/oauth/authorize?{urlencode({'response_type':'code','client_id':'muslim-llm-context-broker','redirect_uri':redirect_uri,'state':state,'code_challenge':challenge,'code_challenge_method':'S256'})}"
