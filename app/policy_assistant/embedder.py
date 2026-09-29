from typing import Protocol

from openai import AsyncOpenAI

from app.llmops.tracing import trace_call

EMBEDDING_PROMPT_VERSION = "embedding-v1"


class Embedder(Protocol):
    async def embed(self, *, text: str) -> list[float]: ...


class OpenAIEmbedder:
    def __init__(self, *, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def embed(self, *, text: str) -> list[float]:
        async with trace_call(
            call_type="embedding",
            model=self.model,
            prompt_version=EMBEDDING_PROMPT_VERSION,
        ) as usage:
            response = await self.client.embeddings.create(
                model=self.model, input=text
            )
            usage["input_tokens"] = response.usage.prompt_tokens
            embedding = response.data[0].embedding

        return embedding
