import asyncio
from datetime import UTC, datetime
from pathlib import Path

import httpx
import yaml


CAPABILITIES_PATH = Path(__file__).with_name("provider_capabilities.yaml")


async def verify() -> int:
    payload = yaml.safe_load(CAPABILITIES_PATH.read_text(encoding="utf-8"))
    providers = payload.get("providers", [])
    verified = 0
    async with httpx.AsyncClient(timeout=5, follow_redirects=False) as client:
        for provider in providers:
            if provider["provider_id"] != "demo":
                if provider.get("consumer_history_api") and not provider.get("verification_source"):
                    raise RuntimeError(f"{provider['provider_id']} claims history access without a verification source")
                continue
            broker = await client.get("http://127.0.0.1:8100/v1/providers")
            mock = await client.get("http://127.0.0.1:8200/health")
            broker.raise_for_status()
            mock.raise_for_status()
            broker_demo = next((item for item in broker.json() if item["provider_id"] == "demo"), None)
            if not broker_demo or not broker_demo["available"]:
                raise RuntimeError("Demo provider is not enabled by the authorization broker")
            provider["verified_at"] = datetime.now(UTC).date().isoformat()
            provider["verification_source"] = "local_mock_provider_e2e"
            verified += 1
    CAPABILITIES_PATH.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    print(f"Verified {verified} direct provider capability set(s). No commercial provider was promoted.")
    return verified


if __name__ == "__main__":
    asyncio.run(verify())
