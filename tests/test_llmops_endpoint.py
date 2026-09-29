import asyncio

from fastapi.testclient import TestClient

from app.llmops.tracing import record_llm_trace
from app.main import app


def test_trace_summary_endpoint_returns_aggregated_rows() -> None:
    asyncio.run(
        record_llm_trace(
            call_type="extraction",
            model="gpt-5-mini",
            prompt_version="extraction-v1",
            latency_ms=100,
            status="success",
            input_tokens=10,
            output_tokens=5,
        )
    )

    with TestClient(app) as client:
        response = client.get("/llmops/traces/summary")

    assert response.status_code == 200
    rows = response.json()
    matching = [
        row
        for row in rows
        if row["call_type"] == "extraction" and row["prompt_version"] == "extraction-v1"
    ]
    assert len(matching) == 1
    assert matching[0]["call_count"] == 1
    assert matching[0]["success_count"] == 1
