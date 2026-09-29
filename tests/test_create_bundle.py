from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_created_bundle_can_be_read_back() -> None:
    tenant_id = f"test-{uuid4().hex}"

    with TestClient(app) as client:
        create_response = client.post(
            "/bundles",
            json={"tenant_id": tenant_id},
        )

        assert create_response.status_code == 201

        created_bundle = create_response.json()

        get_response = client.get(f"/bundles/{created_bundle['id']}")

    assert get_response.status_code == 200

    retrieved_bundle = get_response.json()

    assert retrieved_bundle["id"] == created_bundle["id"]
    assert retrieved_bundle["tenant_id"] == tenant_id
    assert retrieved_bundle["status"] == "received"
