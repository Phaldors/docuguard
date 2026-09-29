from app.policy_assistant.corpus import PolicyChunk
from app.policy_assistant.retrieval import (
    IndexedChunk,
    bm25_rank,
    cosine_similarity,
    hybrid_search,
    reciprocal_rank_fusion,
    semantic_rank,
    tokenize,
)


def make_indexed(chunk_id: str, text: str, embedding: list[float]) -> IndexedChunk:
    return IndexedChunk(
        chunk=PolicyChunk(
            chunk_id=chunk_id,
            document_path="docs/example.md",
            heading="Example",
            text=text,
        ),
        embedding=embedding,
    )


def test_tokenize_lowercases_and_strips_punctuation() -> None:
    assert tokenize("Routing Policy: always review!") == [
        "routing",
        "policy",
        "always",
        "review",
    ]


def test_bm25_ranks_the_matching_chunk_above_an_unrelated_one() -> None:
    chunks = [
        make_indexed("a", "The routing policy always routes to human review.", []),
        make_indexed("b", "Bananas are a good source of potassium.", []),
    ]

    ranking = bm25_rank("routing policy review", chunks)

    assert ranking[0] == "a"


def test_bm25_drops_chunks_that_share_no_term_with_the_query() -> None:
    chunks = [
        make_indexed("a", "Bananas are a good source of potassium.", []),
    ]

    ranking = bm25_rank("routing policy review", chunks)

    assert ranking == []


def test_cosine_similarity_of_identical_vectors_is_one() -> None:
    assert cosine_similarity([1.0, 0.0], [1.0, 0.0]) == 1.0


def test_cosine_similarity_of_orthogonal_vectors_is_zero() -> None:
    assert cosine_similarity([1.0, 0.0], [0.0, 1.0]) == 0.0


def test_semantic_rank_orders_by_similarity_to_the_query_embedding() -> None:
    chunks = [
        make_indexed("close", "text", [1.0, 0.0]),
        make_indexed("far", "text", [0.0, 1.0]),
    ]

    ranking = semantic_rank([0.9, 0.1], chunks)

    assert ranking == ["close", "far"]


def test_reciprocal_rank_fusion_favours_items_both_rankings_agree_on() -> None:
    lexical = ["a", "b", "c"]
    semantic = ["b", "a", "c"]

    fused = reciprocal_rank_fusion([lexical, semantic])

    # "a" and "b" both rank in the top two of both lists; "c" is last in both.
    assert fused[-1] == "c"
    assert set(fused[:2]) == {"a", "b"}


def test_hybrid_search_combines_lexical_and_semantic_signals() -> None:
    chunks = [
        make_indexed(
            "routing",
            "The routing policy always routes to human review.",
            [1.0, 0.0],
        ),
        make_indexed(
            "unrelated",
            "Bananas are a good source of potassium.",
            [0.0, 1.0],
        ),
    ]

    results = hybrid_search("routing policy", chunks, [0.9, 0.1], limit=2)

    assert results[0].chunk.chunk_id == "routing"
