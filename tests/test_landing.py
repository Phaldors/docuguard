from fastapi.testclient import TestClient

from app.main import app


def test_public_root_redirects_to_the_reviewer_console() -> None:
    with TestClient(app) as client:
        response = client.get("/", follow_redirects=False)

    assert response.status_code == 307
    assert response.headers["location"] == "/reviewer"
