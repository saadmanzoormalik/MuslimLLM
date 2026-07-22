from .chatgpt import ChatGPTConnector
from .claude import ClaudeConnector
from .copilot import CopilotConnector
from .deepseek import DeepSeekConnector
from .demo import DemoConnector
from .gemini import GeminiConnector
from .generic_export import GenericExportConnector
from .glm import GLMConnector
from .grok import GrokConnector
from .perplexity import PerplexityConnector
from .qwen import QwenConnector


CONNECTORS = {
    "demo": DemoConnector,
    "chatgpt": ChatGPTConnector,
    "claude": ClaudeConnector,
    "gemini": GeminiConnector,
    "copilot": CopilotConnector,
    "perplexity": PerplexityConnector,
    "deepseek": DeepSeekConnector,
    "grok": GrokConnector,
    "qwen": QwenConnector,
    "glm": GLMConnector,
    "other": GenericExportConnector,
}


def get_connector(provider_id: str):
    return CONNECTORS.get(provider_id, GenericExportConnector)()
