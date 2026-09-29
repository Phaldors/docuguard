import asyncio
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db.session import session_factory
from app.demo.seed import DEMO_BUNDLE_ID, seed_demo
from app.main import app


@pytest.fixture
def public_demo_mode(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("DOCUGUARD_PUBLIC_DEMO", "true")
    monkeypatch.setenv("DOCUGUARD_DEMO_REVIEW_TOKEN", "demo-review-access")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def seed_public_demo() -> None:
    async def seed() -> None:
        async with session_factory() as session:
            await seed_demo(session, replace=True)
            await session.commit()

    asyncio.run(seed())


def test_public_demo_exposes_only_the_synthetic_case(
    public_demo_mode: None,
) -> None:
    seed_public_demo()

    with TestClient(app) as client:
        list_response = client.get("/bundles")
        demo_response = client.get(f"/bundles/{DEMO_BUNDLE_ID}/review")
        other_response = client.get(f"/bundles/{uuid4()}")

    assert [bundle["id"] for bundle in list_response.json()] == [str(DEMO_BUNDLE_ID)]
    assert demo_response.status_code == 200
    assert other_response.status_code == 404


def test_public_demo_blocks_data_creation_and_protected_endpoints(
    public_demo_mode: None,
) -> None:
    with TestClient(app) as client:
        create_response = client.post("/bundles", json={"tenant_id": "untrusted"})
        reconcile_response = client.post(f"/bundles/{DEMO_BUNDLE_ID}/reconcile")
        policy_response = client.post(
            "/policy-assistant/ask", json={"question": "Should this run?"}
        )
        traces_response = client.get("/llmops/traces/summary")

    for response in (
        create_response,
        reconcile_response,
        policy_response,
        traces_response,
    ):
        assert response.status_code == 403


def test_public_demo_requires_an_access_code_for_reviewer_actions(
    public_demo_mode: None,
) -> None:
    seed_public_demo()
    payload = {
        "action": "needs_info",
        "actor": "reviewer@example.com",
        "reason": "Need a clearer source document.",
    }

    with TestClient(app) as client:
        denied_response = client.post(f"/bundles/{DEMO_BUNDLE_ID}/decision", json=payload)
        allowed_response = client.post(
            f"/bundles/{DEMO_BUNDLE_ID}/decision",
            headers={"X-DocuGuard-Review-Token": "demo-review-access"},
            json=payload,
        )

    assert denied_response.status_code == 401
    assert allowed_response.status_code == 200
    assert allowed_response.json()["bundle"]["status"] == "needs_info"
