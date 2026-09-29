from app.policy_assistant.answer import PolicyAnswer, PolicyAssistant
from app.policy_assistant.embedder import Embedder
from app.policy_assistant.reranker import Reranker
from app.policy_assistant.retrieval import IndexedChunk, hybrid_search


class EmptyCorpusError(Exception):
    """Raised when the policy index has no chunks to search."""


async def ask_policy_question(
    *,
    query: str,
    index: list[IndexedChunk],
    embedder: Embedder,
    reranker: Reranker,
    assistant: PolicyAssistant,
    retrieval_limit: int = 12,
    final_limit: int = 4,
) -> PolicyAnswer:
    if not index:
        raise EmptyCorpusError

    query_embedding = await embedder.embed(text=query)
    candidates = hybrid_search(query, index, query_embedding, limit=retrieval_limit)

    by_id = {indexed.chunk.chunk_id: indexed for indexed in index}
    candidate_chunks = [
        by_id[scored.chunk.chunk_id]
        for scored in candidates
        if scored.chunk.chunk_id in by_id
    ]

    rankings = await reranker.rerank(query=query, candidates=candidate_chunks)
    ranked_ids = [
        ranking.chunk_id
        for ranking in sorted(
            rankings, key=lambda ranking: ranking.relevance_score, reverse=True
        )
    ]
    # Rerank scores every candidate, but if the reranker drops one, fall back
    # to the hybrid-search order rather than silently losing a passage.
    fallback_order = [scored.chunk.chunk_id for scored in candidates]
    ordered_ids = ranked_ids + [
        chunk_id for chunk_id in fallback_order if chunk_id not in ranked_ids
    ]

    passages = [by_id[chunk_id] for chunk_id in ordered_ids[:final_limit]]
    return await assistant.answer(query=query, passages=passages)
