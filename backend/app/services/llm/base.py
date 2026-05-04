"""Base LLM client interface."""

from abc import ABC, abstractmethod


class LLMClient(ABC):
    """Abstract base for LLM providers."""

    def __init__(self, api_key: str, model: str, base_url: str | None = None):
        self.api_key = api_key
        self.model = model
        self.base_url = base_url

    @abstractmethod
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        """Generate text from system + user prompts. Returns the response text."""
        ...
