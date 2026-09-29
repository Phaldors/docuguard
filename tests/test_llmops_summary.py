import pytest

from app.db.session import session_factory
from app.llmops.tracing import record_llm_trace
from app.services.llmops import summarize_traces


@pytest.mark.asyncio
async def test_summarize_traces_aggregates_by_call_type_model_and_prompt_version() -> (
    None
):
    await record_llm_trace(
        call_type="extraction", model="gpt-5-mini", prompt_version="extraction-v1",
        latency_ms=100, status="success", input_tokens=10, output_tokens=5,
    )
    await record_llm_trace(
        call_type="extraction", model="gpt-5-mini", prompt_version="extraction-v1",
        latency_ms=200, status="error", error_message="timeout",
    )
    await record_llm_trace(
        call_type="embedding", model="text-embedding-3-small", prompt_version="v1",
        latency_ms=50, status="success", input_tokens=8,
    )

    async with session_factory() as session:
        rows = await summarize_traces(session=session)

    by_key = {(row.call_type, row.model, row.prompt_version): row for row in rows}

    extraction_row = by_key[("extraction", "gpt-5-mini", "extraction-v1")]
    assert extraction_row.call_count == 2
    assert extraction_row.success_count == 1
    assert extraction_row.error_count == 1
    assert extraction_row.avg_latency_ms == 150.0
    assert extraction_row.total_input_tokens == 10
    assert extraction_row.total_output_tokens == 5

    embedding_row = by_key[("embedding", "text-embedding-3-small", "v1")]
    assert embedding_row.call_count == 1
    assert embedding_row.success_count == 1
    assert embedding_row.total_input_tokens == 8
