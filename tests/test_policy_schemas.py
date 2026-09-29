from app.policy_assistant.answer import Citation, PolicyAnswer
from app.policy_assistant.reranker import ChunkRelevance, RerankResult


def test_policy_answer_schema_forbids_unexpected_properties() -> None:
    assert PolicyAnswer.model_json_schema()["additionalProperties"] is False
    assert Citation.model_json_schema()["additionalProperties"] is False


def test_policy_answer_accepts_a_grounded_answer_with_citations() -> None:
    answer = PolicyAnswer.model_validate(
        {
            "answer": "A critical reconciliation rule always routes to review.",
            "grounded": True,
            "citations": [
                {
                    "chunk_id": "reviewer-workflow.md#2",
                    "quote": "a critical reconciliation rule is violated",
                }
            ],
        }
    )

    assert answer.grounded is True
    assert answer.citations[0].chunk_id == "reviewer-workflow.md#2"


def test_policy_answer_accepts_an_ungrounded_answer() -> None:
    answer = PolicyAnswer.model_validate(
        {
            "answer": "The policy corpus does not cover this question.",
            "grounded": False,
            "citations": [],
        }
    )

    assert answer.grounded is False
    assert answer.citations == []


def test_rerank_result_schema_forbids_unexpected_properties() -> None:
    assert RerankResult.model_json_schema()["additionalProperties"] is False
    assert ChunkRelevance.model_json_schema()["additionalProperties"] is False


def test_rerank_result_accepts_scored_candidates() -> None:
    result = RerankResult.model_validate(
        {
            "rankings": [
                {"chunk_id": "a", "relevance_score": 0.9},
                {"chunk_id": "b", "relevance_score": 0.1},
            ]
        }
    )

    assert result.rankings[0].chunk_id == "a"
