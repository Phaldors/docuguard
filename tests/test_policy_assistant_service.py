import pytest

from app.policy_assistant.answer import Citation, PolicyAnswer
from app.policy_assistant.corpus import PolicyChunk
from app.policy_assistant.reranker import ChunkRelevance
from app.policy_assistant.retrieval import IndexedChunk
from app.services.policy_assistant import EmptyCorpusError, ask_policy_question


def make_indexed(chunk_id: str, text: str = "some policy text") -> IndexedChunk:
    return IndexedChunk(
        chunk=PolicyChunk(
            chunk_id=chunk_id,
            document_path="docs/example.md",
            heading="Example",
            text=text,
        ),
        embedding=[1.0, 0.0],
    )


class FakeEmbedder:
    async def embed(self, *, text: str) -> list[float]:
        return [1.0, 0.0]


class FakeReranker:
    def __init__(self, rankings: list[ChunkRelevance]) -> None:
        self.rankings = rankings
        self.received_candidates: list[IndexedChunk] | None = None

    async def rerank(
        self, *, query: str, candidates: list[IndexedChunk]
    ) -> list[ChunkRelevance]:
        self.received_candidates = candidates
        return self.rankings


class FakeAssistant:
    def __init__(self, answer: PolicyAnswer) -> None:
        self.answer_to_return = answer
        self.received_passages: list[IndexedChunk] | None = None

    async def answer(
        self, *, query: str, passages: list[IndexedChunk]
    ) -> PolicyAnswer:
        self.received_passages = passages
        return self.answer_to_return


@pytest.mark.asyncio
async def test_ask_policy_question_returns_the_assistants_answer() -> None:
    index = [make_indexed("a"), make_indexed("b")]
    expected = PolicyAnswer(
        answer="Answer.",
        grounded=True,
        citations=[Citation(chunk_id="a", quote="some policy text")],
    )

    result = await ask_policy_question(
        query="What is the routing policy?",
        index=index,
        embedder=FakeEmbedder(),
        reranker=FakeReranker(
            [
                ChunkRelevance(chunk_id="a", relevance_score=0.9),
                ChunkRelevance(chunk_id="b", relevance_score=0.1),
            ]
        ),
        assistant=FakeAssistant(expected),
    )

    assert result == expected


@pytest.mark.asyncio
async def test_ask_policy_question_raises_for_an_empty_index() -> None:
    with pytest.raises(EmptyCorpusError):
        await ask_policy_question(
            query="What is the routing policy?",
            index=[],
            embedder=FakeEmbedder(),
            reranker=FakeReranker([]),
            assistant=FakeAssistant(
                PolicyAnswer(answer="N/A", grounded=False, citations=[])
            ),
        )


@pytest.mark.asyncio
async def test_ask_policy_question_orders_passages_by_reranker_score() -> None:
    index = [make_indexed("a"), make_indexed("b")]
    assistant = FakeAssistant(
        PolicyAnswer(answer="Answer.", grounded=True, citations=[])
    )

    await ask_policy_question(
        query="What is the routing policy?",
        index=index,
        embedder=FakeEmbedder(),
        reranker=FakeReranker(
            [
                ChunkRelevance(chunk_id="b", relevance_score=0.9),
                ChunkRelevance(chunk_id="a", relevance_score=0.1),
            ]
        ),
        assistant=assistant,
    )

    assert [indexed.chunk.chunk_id for indexed in assistant.received_passages] == [
        "b",
        "a",
    ]


@pytest.mark.asyncio
async def test_ask_policy_question_falls_back_to_hybrid_order_for_dropped_candidates() -> (
    None
):
    index = [make_indexed("a"), make_indexed("b")]
    assistant = FakeAssistant(
        PolicyAnswer(answer="Answer.", grounded=True, citations=[])
    )

    # The reranker only scores "a"; "b" should still appear, via fallback order.
    await ask_policy_question(
        query="What is the routing policy?",
        index=index,
        embedder=FakeEmbedder(),
        reranker=FakeReranker([ChunkRelevance(chunk_id="a", relevance_score=0.9)]),
        assistant=assistant,
    )

    passage_ids = {indexed.chunk.chunk_id for indexed in assistant.received_passages}
    assert passage_ids == {"a", "b"}
