from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app


def test_get_missing_bundle_returns_not_found() -> None:
    with TestClient(app) as client:
        response = client.get(f"/bundles/{uuid4()}")

    assert response.status_code == 404
    assert response.json() == {"detail": "Document bundle was not found."}
