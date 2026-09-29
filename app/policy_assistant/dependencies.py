from functools import lru_cache

from app.config import get_settings
from app.policy_assistant.answer import LLMPolicyAssistant, PolicyAssistant
from app.policy_assistant.embedder import Embedder, OpenAIEmbedder
from app.policy_assistant.reranker import LLMReranker, Reranker
from app.policy_assistant.retrieval import (
    DEFAULT_INDEX_PATH,
    IndexedChunk,
    load_index,
)


@lru_cache
def get_policy_index() -> list[IndexedChunk]:
    if not DEFAULT_INDEX_PATH.exists():
        return []

    return load_index()


@lru_cache
def get_embedder() -> Embedder | None:
    settings = get_settings()
    if settings.openai_api_key is None:
        return None

    return OpenAIEmbedder(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.embedding_model,
    )


@lru_cache
def get_reranker() -> Reranker | None:
    settings = get_settings()
    if settings.openai_api_key is None:
        return None

    return LLMReranker(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.reranker_model,
    )


@lru_cache
def get_policy_assistant() -> PolicyAssistant | None:
    settings = get_settings()
    if settings.openai_api_key is None:
        return None

    return LLMPolicyAssistant(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.policy_assistant_model,
    )
