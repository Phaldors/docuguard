from fastapi.testclient import TestClient

from app.main import app


def test_get_document_returns_metadata_before_extraction() -> None:
    with TestClient(app) as client:
        bundle_response = client.post(
            "/bundles",
            json={"tenant_id": "document-details-test"},
        )
        bundle_id = bundle_response.json()["id"]
        upload_response = client.post(
            f"/bundles/{bundle_id}/documents",
            files={
                "file": (
                    "invoice.pdf",
                    b"%PDF-1.7 document details",
                    "application/pdf",
                ),
            },
        )
        document_id = upload_response.json()["id"]

        response = client.get(f"/bundles/{bundle_id}/documents/{document_id}")

    assert bundle_response.status_code == 201
    assert upload_response.status_code == 201
    assert response.status_code == 200
    assert response.json()["id"] == document_id
    assert response.json()["processing_status"] == "queued"
    assert response.json()["extraction"] is None
