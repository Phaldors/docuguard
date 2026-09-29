from pydantic import BaseModel


class TraceSummaryResponse(BaseModel):
    call_type: str
    model: str
    prompt_version: str
    call_count: int
    success_count: int
    error_count: int
    avg_latency_ms: float
    total_input_tokens: int
    total_output_tokens: int
