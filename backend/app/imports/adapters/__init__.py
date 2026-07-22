from .anthropic_claude import ClaudeAdapter
from .deepseek import DeepSeekAdapter
from .generic_json import GenericJsonAdapter
from .generic_markdown import GenericMarkdownAdapter
from .glm import GLMAdapter
from .google_gemini import GeminiAdapter
from .grok import GrokAdapter
from .openai_chatgpt import ChatGPTAdapter
from .qwen import QwenAdapter


def provider_adapters():
    adapters = [
        ChatGPTAdapter(),
        ClaudeAdapter(),
        GeminiAdapter(),
        DeepSeekAdapter(),
        GrokAdapter(),
        QwenAdapter(),
        GLMAdapter(),
        GenericJsonAdapter(),
        GenericMarkdownAdapter(),
    ]
    return {adapter.provider_name: adapter for adapter in adapters}


def get_adapter(provider: str):
    adapters = provider_adapters()
    key = provider.lower().replace("openai", "chatgpt").replace("anthropic", "claude")
    return adapters.get(key) or adapters.get("generic_json")
