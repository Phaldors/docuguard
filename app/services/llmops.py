from dataclasses import dataclass

from sqlalchemy import case, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.llm_trace import LLMTrace


@dataclass(frozen=True)
class TraceSummaryRow:
    call_type: str
    model: str
    prompt_version: str
    call_count: int
    success_count: int
    error_count: int
    avg_latency_ms: float
    total_input_tokens: int
    total_output_tokens: int


async def summarize_traces(*, session: AsyncSession) -> list[TraceSummaryRow]:
    result = await session.execute(
        select(
            LLMTrace.call_type,
            LLMTrace.model,
            LLMTrace.prompt_version,
            func.count().label("call_count"),
            func.sum(case((LLMTrace.status == "success", 1), else_=0)).label(
                "success_count"
            ),
            func.sum(case((LLMTrace.status == "error", 1), else_=0)).label(
                "error_count"
            ),
            func.avg(LLMTrace.latency_ms).label("avg_latency_ms"),
            func.coalesce(func.sum(LLMTrace.input_tokens), 0).label(
                "total_input_tokens"
            ),
            func.coalesce(func.sum(LLMTrace.output_tokens), 0).label(
                "total_output_tokens"
            ),
        )
        .group_by(LLMTrace.call_type, LLMTrace.model, LLMTrace.prompt_version)
        .order_by(LLMTrace.call_type, LLMTrace.model, LLMTrace.prompt_version)
    )

    return [
        TraceSummaryRow(
            call_type=row.call_type,
            model=row.model,
            prompt_version=row.prompt_version,
            call_count=row.call_count,
            success_count=row.success_count or 0,
            error_count=row.error_count or 0,
            avg_latency_ms=float(row.avg_latency_ms or 0),
            total_input_tokens=row.total_input_tokens,
            total_output_tokens=row.total_output_tokens,
        )
        for row in result
    ]
