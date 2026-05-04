"""Anthropic Claude LLM client."""

from anthropic import AsyncAnthropic
from anthropic.types import Message

from app.services.llm.base import LLMClient


class AnthropicClient(LLMClient):
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        client = AsyncAnthropic(api_key=self.api_key, base_url=self.base_url)
        response: Message = await client.messages.create(
            model=self.model,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}],
        )
        return response.content[0].text  # type: ignore[union-attr]
