import httpx

from ..config import settings


async def exchange_demo_code(code: str, verifier: str, redirect_uri: str) -> dict:
    async with httpx.AsyncClient(timeout=15, follow_redirects=False) as client:
        response = await client.post(
            f"{settings.mock_provider_url}/oauth/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "client_id": "muslim-llm-context-broker",
                "code_verifier": verifier,
                "redirect_uri": redirect_uri,
            },
        )
        response.raise_for_status()
        return response.json()
