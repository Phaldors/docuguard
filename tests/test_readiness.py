from fastapi.testclient import TestClient

from app.main import app


def test_readiness_check_confirms_database_connection() -> None:
    with TestClient(app) as client:
        response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ready"}
