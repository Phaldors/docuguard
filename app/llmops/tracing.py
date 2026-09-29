"""Records an LLMTrace for every LLM call in the system.

Deliberately independent of the caller's own database session/transaction:
a trace is observability data, not business data, and should still be
recorded even if the caller's transaction later rolls back (e.g. the
extraction succeeded and is worth tracing even if a later step in the same
request fails). Each call opens and commits its own short-lived session.
"""

import time
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

from app.db.session import session_factory
from app.llmops.redaction import redact_pii
from app.models.llm_trace import LLMTrace


async def record_llm_trace(
    *,
    call_type: str,
    model: str,
    prompt_version: str,
    latency_ms: int,
    status: str,
    correlation_id: str | None = None,
    input_tokens: int | None = None,
    output_tokens: int | None = None,
    error_message: str | None = None,
) -> None:
    async with session_factory() as session:
        session.add(
            LLMTrace(
                call_type=call_type,
                model=model,
                prompt_version=prompt_version,
                correlation_id=correlation_id,
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                latency_ms=latency_ms,
                status=status,
                error_message=redact_pii(error_message) if error_message else None,
            )
        )
        await session.commit()


@asynccontextmanager
async def trace_call(
    *,
    call_type: str,
    model: str,
    prompt_version: str,
    correlation_id: str | None = None,
) -> AsyncIterator[dict[str, int | None]]:
    """Times the wrapped block and records one LLMTrace on exit, whether it
    succeeds or raises. Set usage["input_tokens"]/usage["output_tokens"] on
    the yielded dict once the real response is available; they default to
    None (e.g. for a call that fails before a response comes back)."""
    usage: dict[str, int | None] = {"input_tokens": None, "output_tokens": None}
    start = time.monotonic()
    try:
        yield usage
    except Exception as error:
        await record_llm_trace(
            call_type=call_type,
            model=model,
            prompt_version=prompt_version,
            correlation_id=correlation_id,
            latency_ms=int((time.monotonic() - start) * 1000),
            status="error",
            error_message=str(error),
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )
        raise
    else:
        await record_llm_trace(
            call_type=call_type,
            model=model,
            prompt_version=prompt_version,
            correlation_id=correlation_id,
            latency_ms=int((time.monotonic() - start) * 1000),
            status="success",
            input_tokens=usage["input_tokens"],
            output_tokens=usage["output_tokens"],
        )
