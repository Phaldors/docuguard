import pytest
from sqlalchemy import select

from app.db.session import session_factory
from app.llmops.tracing import record_llm_trace, trace_call
from app.models.llm_trace import LLMTrace


@pytest.mark.asyncio
async def test_record_llm_trace_persists_a_row() -> None:
    await record_llm_trace(
        call_type="extraction",
        model="gpt-5-mini",
        prompt_version="extraction-v1",
        latency_ms=42,
        status="success",
        input_tokens=100,
        output_tokens=50,
    )

    async with session_factory() as session:
        trace = await session.scalar(
            select(LLMTrace).where(LLMTrace.call_type == "extraction")
        )

    assert trace is not None
    assert trace.model == "gpt-5-mini"
    assert trace.prompt_version == "extraction-v1"
    assert trace.status == "success"
    assert trace.input_tokens == 100
    assert trace.output_tokens == 50


@pytest.mark.asyncio
async def test_record_llm_trace_redacts_pii_in_error_message() -> None:
    await record_llm_trace(
        call_type="extraction",
        model="gpt-5-mini",
        prompt_version="extraction-v1",
        latency_ms=10,
        status="error",
        error_message="failed for user jane@example.com",
    )

    async with session_factory() as session:
        trace = await session.scalar(
            select(LLMTrace).where(LLMTrace.call_type == "extraction")
        )

    assert trace is not None
    assert "jane@example.com" not in trace.error_message
    assert "[REDACTED_EMAIL]" in trace.error_message


@pytest.mark.asyncio
async def test_trace_call_records_success_with_usage() -> None:
    async with trace_call(
        call_type="embedding", model="text-embedding-3-small", prompt_version="v1"
    ) as usage:
        usage["input_tokens"] = 12

    async with session_factory() as session:
        trace = await session.scalar(
            select(LLMTrace).where(LLMTrace.call_type == "embedding")
        )

    assert trace is not None
    assert trace.status == "success"
    assert trace.input_tokens == 12
    assert trace.latency_ms >= 0


@pytest.mark.asyncio
async def test_trace_call_records_error_and_reraises() -> None:
    with pytest.raises(RuntimeError, match="boom"):
        async with trace_call(
            call_type="rerank", model="gpt-5-mini", prompt_version="v1"
        ):
            raise RuntimeError("boom")

    async with session_factory() as session:
        trace = await session.scalar(
            select(LLMTrace).where(LLMTrace.call_type == "rerank")
        )

    assert trace is not None
    assert trace.status == "error"
    assert trace.error_message == "boom"
