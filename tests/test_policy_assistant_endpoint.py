from fastapi.testclient import TestClient

from app.main import app
from app.policy_assistant.answer import Citation, PolicyAnswer
from app.policy_assistant.corpus import PolicyChunk
from app.policy_assistant.dependencies import (
    get_embedder,
    get_policy_assistant,
    get_policy_index,
    get_reranker,
)
from app.policy_assistant.reranker import ChunkRelevance
from app.policy_assistant.retrieval import IndexedChunk


def make_index() -> list[IndexedChunk]:
    return [
        IndexedChunk(
            chunk=PolicyChunk(
                chunk_id="reviewer-workflow.md#0",
                document_path="docs/reviewer-workflow.md",
                heading="Routing policy",
                text="Always route to review when a critical rule is violated.",
            ),
            embedding=[1.0, 0.0],
        )
    ]


class FakeEmbedder:
    async def embed(self, *, text: str) -> list[float]:
        return [1.0, 0.0]


class FakeReranker:
    async def rerank(self, *, query: str, candidates):
        return [
            ChunkRelevance(chunk_id=indexed.chunk.chunk_id, relevance_score=1.0)
            for indexed in candidates
        ]


def empty_index() -> list[IndexedChunk]:
    return []


class FakeAssistant:
    async def answer(self, *, query: str, passages):
        return PolicyAnswer(
            answer="Always route to review when a critical rule is violated.",
            grounded=True,
            citations=[
                Citation(
                    chunk_id="reviewer-workflow.md#0",
                    quote="Always route to review when a critical rule is violated.",
                )
            ],
        )


def test_ask_policy_question_returns_a_grounded_cited_answer() -> None:
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_reranker] = lambda: FakeReranker()
    app.dependency_overrides[get_policy_assistant] = lambda: FakeAssistant()
    app.dependency_overrides[get_policy_index] = make_index

    try:
        with TestClient(app) as client:
            response = client.post(
                "/policy-assistant/ask",
                json={"question": "When does a case always go to review?"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 200
    body = response.json()
    assert body["grounded"] is True
    assert body["citations"][0]["chunk_id"] == "reviewer-workflow.md#0"
    assert body["citations"][0]["document_path"] == "docs/reviewer-workflow.md"


def test_ask_policy_question_returns_503_when_not_configured() -> None:
    app.dependency_overrides[get_embedder] = lambda: None
    app.dependency_overrides[get_reranker] = lambda: None
    app.dependency_overrides[get_policy_assistant] = lambda: None
    app.dependency_overrides[get_policy_index] = empty_index

    try:
        with TestClient(app) as client:
            response = client.post(
                "/policy-assistant/ask",
                json={"question": "When does a case always go to review?"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503


def test_ask_policy_question_returns_503_for_an_empty_index() -> None:
    app.dependency_overrides[get_embedder] = lambda: FakeEmbedder()
    app.dependency_overrides[get_reranker] = lambda: FakeReranker()
    app.dependency_overrides[get_policy_assistant] = lambda: FakeAssistant()
    app.dependency_overrides[get_policy_index] = empty_index

    try:
        with TestClient(app) as client:
            response = client.post(
                "/policy-assistant/ask",
                json={"question": "When does a case always go to review?"},
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 503
