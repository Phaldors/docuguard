import asyncio

from fastapi.testclient import TestClient

from app.db.session import session_factory
from app.demo.seed import DEMO_BUNDLE_ID, seed_demo
from app.main import app


def test_reviewer_case_endpoint_returns_evidence_findings_and_audit_history() -> None:
    async def seed() -> None:
        async with session_factory() as session:
            await seed_demo(session, replace=True)
            await session.commit()

    asyncio.run(seed())

    with TestClient(app) as client:
        response = client.get(f"/bundles/{DEMO_BUNDLE_ID}/review")

    assert response.status_code == 200
    body = response.json()
    assert body["bundle"]["status"] == "ready_for_review"
    assert len(body["documents"]) == 3
    assert body["documents"][0]["extraction"] is not None
    assert "Invoice total" in body["documents"][0]["extraction"]["text_content"]
    assert body["documents"][0]["fields"] is not None
    assert {item["discrepancy_type"] for item in body["discrepancies"]} == {
        "low_confidence_field",
        "total_mismatch",
    }
    assert body["audit_events"] == []


def test_reviewer_page_is_served() -> None:
    with TestClient(app) as client:
        response = client.get("/reviewer")

    assert response.status_code == 200
    assert "Reviewer Console" in response.text
