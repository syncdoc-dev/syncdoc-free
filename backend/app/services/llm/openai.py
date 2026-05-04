"""OpenAI LLM client."""

from openai import AsyncOpenAI

from app.services.llm.base import LLMClient


class OpenAIClient(LLMClient):
    async def generate(self, system_prompt: str, user_prompt: str) -> str:
        client = AsyncOpenAI(api_key=self.api_key, base_url=self.base_url)
        response = await client.chat.completions.create(
            model=self.model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            max_tokens=4096,
        )
        return response.choices[0].message.content or ""
