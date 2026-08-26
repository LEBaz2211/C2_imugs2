"""Composition helper for the production LangChain provider."""

from __future__ import annotations

from .config import AssistantSettings
from .orchestrator import AssistantOrchestrator, OperationalContextSource
from .prompts import PromptCatalog
from .provider import LangChainOpenAIProvider


def build_assistant(
    context: OperationalContextSource,
    *,
    settings: AssistantSettings | None = None,
    prompt_catalog: PromptCatalog | None = None,
) -> AssistantOrchestrator:
    """Build the default LM Studio assistant without making a server request."""

    resolved = settings or AssistantSettings.from_env()
    provider = LangChainOpenAIProvider(resolved)
    return AssistantOrchestrator(
        context=context,
        model=provider,
        settings=resolved,
        prompt_catalog=prompt_catalog,
    )
