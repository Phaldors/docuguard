"""Hybrid (lexical + semantic) retrieval over the policy corpus.

Everything in this module is pure and deterministic given its inputs: no
network calls. BM25 needs no embedding at all, and the cosine-similarity
step takes a precomputed query embedding rather than computing it itself,
so the whole ranking pipeline is unit-testable without OpenAI.
"""

import json
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from app.policy_assistant.corpus import PolicyChunk

DEFAULT_INDEX_PATH = Path("docs/policy-index/index.json")

_TOKEN_PATTERN = re.compile(r"[a-z0-9]+")

# BM25 has no notion of semantic importance -- without this, a query like
# "does the case still need a human reviewer" spends most of its term budget
# on words that appear in nearly every chunk ("the", "does", "a", "need"),
# diluting the two words that actually distinguish the right passage
# ("missing", "required"). This list is intentionally short: only the
# highest-frequency function words, not a full stopword corpus.
_STOPWORDS = frozenset(
    {
        "a", "an", "the", "is", "are", "was", "were", "be", "been", "being",
        "do", "does", "did", "if", "of", "to", "in", "on", "for", "and",
        "or", "but", "with", "this", "that", "it", "its", "as", "at", "by",
        "from", "not", "no", "can", "will", "would", "should", "could",
    }
)


@dataclass(frozen=True)
class IndexedChunk:
    chunk: PolicyChunk
    embedding: list[float]


@dataclass(frozen=True)
class ScoredChunk:
    chunk: PolicyChunk
    score: float


def tokenize(text: str) -> list[str]:
    return [
        token
        for token in _TOKEN_PATTERN.findall(text.lower())
        if token not in _STOPWORDS
    ]


def save_index(chunks: list[IndexedChunk], *, path: Path = DEFAULT_INDEX_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [
        {
            "chunk_id": indexed.chunk.chunk_id,
            "document_path": indexed.chunk.document_path,
            "heading": indexed.chunk.heading,
            "text": indexed.chunk.text,
            "embedding": indexed.embedding,
        }
        for indexed in chunks
    ]
    path.write_text(json.dumps(payload, indent=2))


def load_index(*, path: Path = DEFAULT_INDEX_PATH) -> list[IndexedChunk]:
    payload = json.loads(path.read_text())
    return [
        IndexedChunk(
            chunk=PolicyChunk(
                chunk_id=row["chunk_id"],
                document_path=row["document_path"],
                heading=row["heading"],
                text=row["text"],
            ),
            embedding=row["embedding"],
        )
        for row in payload
    ]


def bm25_rank(query: str, chunks: list[IndexedChunk], *, k1: float = 1.5, b: float = 0.75) -> list[str]:
    """Returns chunk_ids ranked by BM25 score, best first. Chunks that share
    no term with the query are dropped rather than ranked last."""
    query_terms = tokenize(query)
    if not query_terms or not chunks:
        return []

    documents = [tokenize(indexed.chunk.text) for indexed in chunks]
    doc_lengths = [len(document) for document in documents]
    average_length = sum(doc_lengths) / len(doc_lengths) if doc_lengths else 0.0
    document_count = len(documents)

    document_frequency: Counter[str] = Counter()
    for document in documents:
        document_frequency.update(set(document))

    scores: list[tuple[str, float]] = []
    for indexed, document, length in zip(chunks, documents, doc_lengths, strict=True):
        term_counts = Counter(document)
        score = 0.0
        for term in query_terms:
            frequency = term_counts.get(term, 0)
            if frequency == 0:
                continue
            df = document_frequency.get(term, 0)
            idf = math.log(1 + (document_count - df + 0.5) / (df + 0.5))
            denominator = frequency + k1 * (1 - b + b * length / (average_length or 1))
            score += idf * (frequency * (k1 + 1)) / denominator
        if score > 0:
            scores.append((indexed.chunk.chunk_id, score))

    scores.sort(key=lambda item: item[1], reverse=True)
    return [chunk_id for chunk_id, _ in scores]


def cosine_similarity(a: list[float], b: list[float]) -> float:
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(y * y for y in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def semantic_rank(query_embedding: list[float], chunks: list[IndexedChunk]) -> list[str]:
    """Returns chunk_ids ranked by cosine similarity to the query, best first."""
    scored = [
        (indexed.chunk.chunk_id, cosine_similarity(query_embedding, indexed.embedding))
        for indexed in chunks
    ]
    scored = [(chunk_id, score) for chunk_id, score in scored if score > 0]
    scored.sort(key=lambda item: item[1], reverse=True)
    return [chunk_id for chunk_id, _ in scored]


def reciprocal_rank_fusion(
    rankings: list[list[str]], *, k: int = 60
) -> list[str]:
    """Combines several ranked lists into one via Reciprocal Rank Fusion: a
    chunk's fused score is the sum, over every ranking it appears in, of
    1 / (k + its rank there). This favours items several methods agree on
    over an item only one method ranks first, and needs no score
    normalisation across BM25 and cosine similarity, which are not on the
    same scale."""
    scores: dict[str, float] = {}
    for ranking in rankings:
        for rank, chunk_id in enumerate(ranking):
            scores[chunk_id] = scores.get(chunk_id, 0.0) + 1.0 / (k + rank + 1)

    return [
        chunk_id
        for chunk_id, _ in sorted(scores.items(), key=lambda item: item[1], reverse=True)
    ]


def hybrid_search(
    query: str,
    chunks: list[IndexedChunk],
    query_embedding: list[float],
    *,
    limit: int = 8,
) -> list[ScoredChunk]:
    lexical_ranking = bm25_rank(query, chunks)
    semantic_ranking = semantic_rank(query_embedding, chunks)
    fused = reciprocal_rank_fusion([lexical_ranking, semantic_ranking])

    by_id = {indexed.chunk.chunk_id: indexed.chunk for indexed in chunks}
    return [
        ScoredChunk(chunk=by_id[chunk_id], score=1.0 - (position / max(len(fused), 1)))
        for position, chunk_id in enumerate(fused[:limit])
    ]
