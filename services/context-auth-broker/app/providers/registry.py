from .base import ProviderDefinition
from .demo import definition as demo


UNAVAILABLE = [
    ProviderDefinition("chatgpt", "ChatGPT", "official_export", False, False, True),
    ProviderDefinition("claude", "Claude", "official_export", False, False, True),
    ProviderDefinition("gemini", "Gemini", "official_export", False, False, True),
    ProviderDefinition("copilot", "Microsoft Copilot", "unavailable", False, False, False),
    ProviderDefinition("perplexity", "Perplexity", "unavailable", False, False, False),
    ProviderDefinition("deepseek", "DeepSeek", "official_export", False, False, True),
    ProviderDefinition("grok", "Grok", "official_export", False, False, True),
    ProviderDefinition("qwen", "Qwen", "official_export", False, False, True),
    ProviderDefinition("glm", "GLM", "official_export", False, False, True),
]
PROVIDERS = {provider.provider_id: provider for provider in [demo, *UNAVAILABLE]}


def public_providers() -> list[dict]:
    return [provider.__dict__ for provider in PROVIDERS.values()]
