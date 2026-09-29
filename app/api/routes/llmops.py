from typing import Annotated

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.schemas.llmops import TraceSummaryResponse
from app.security.public_demo import block_public_demo_protected_endpoint
from app.services.llmops import summarize_traces

router = APIRouter(prefix="/llmops", tags=["llmops"])


@router.get("/traces/summary", response_model=list[TraceSummaryResponse])
async def get_trace_summary(
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[TraceSummaryResponse]:
    block_public_demo_protected_endpoint()
    rows = await summarize_traces(session=session)
    return [
        TraceSummaryResponse(
            call_type=row.call_type,
            model=row.model,
            prompt_version=row.prompt_version,
            call_count=row.call_count,
            success_count=row.success_count,
            error_count=row.error_count,
            avg_latency_ms=row.avg_latency_ms,
            total_input_tokens=row.total_input_tokens,
            total_output_tokens=row.total_output_tokens,
        )
        for row in rows
    ]
