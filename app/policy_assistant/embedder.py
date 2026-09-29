from typing import Protocol

from openai import AsyncOpenAI


class Embedder(Protocol):
    async def embed(self, *, text: str) -> list[float]: ...


class OpenAIEmbedder:
    def __init__(self, *, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed(self, *, text: str) -> list[float]:
        response = await self.client.embeddings.create(model=self.model, input=text)
        return response.data[0].embedding
