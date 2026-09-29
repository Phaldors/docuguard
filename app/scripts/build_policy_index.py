"""Build the policy assistant's retrieval index.

Chunks the documents in app.policy_assistant.corpus.POLICY_DOCUMENTS,
embeds each chunk, and writes docs/policy-index/index.json. Re-run this
whenever one of those documents changes; the index is a build artifact
checked into the repository, not computed at request time.
"""

import asyncio

from app.config import get_settings
from app.policy_assistant.corpus import load_policy_chunks
from app.policy_assistant.embedder import OpenAIEmbedder
from app.policy_assistant.retrieval import IndexedChunk, save_index


async def build() -> None:
    settings = get_settings()
    if settings.openai_api_key is None:
        raise RuntimeError("DOCUGUARD_OPENAI_API_KEY is required.")

    embedder = OpenAIEmbedder(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.embedding_model,
    )

    chunks = load_policy_chunks()
    indexed = [
        IndexedChunk(chunk=chunk, embedding=await embedder.embed(text=chunk.text))
        for chunk in chunks
    ]
    save_index(indexed)
    print(f"Indexed {len(indexed)} chunks from {len({c.document_path for c in chunks})} documents.")


if __name__ == "__main__":
    asyncio.run(build())
