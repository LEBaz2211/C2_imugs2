"""Natural-language assistant orchestration for the editable C2 backend.

The package deliberately contains no HTTP, MongoDB, ROS, or Docker access.
Callers provide the backend-owned operational context service, while the model
adapter performs one LangChain chat-model invocation for each user message.
"""

from .config import AssistantSettings
from .factory import build_assistant
from .models import (
    AssistantResponse,
    AssistantScenarioBinding,
    AssistantStructuredOutput,
)
from .orchestrator import AssistantBusyError, AssistantOrchestrator
from .provider import ChatModelProvider, LangChainOpenAIProvider

__all__ = [
    "AssistantOrchestrator",
    "AssistantBusyError",
    "AssistantResponse",
    "AssistantScenarioBinding",
    "AssistantSettings",
    "AssistantStructuredOutput",
    "ChatModelProvider",
    "LangChainOpenAIProvider",
    "build_assistant",
]
