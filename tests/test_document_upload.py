from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app
from app.storage.dependencies import get_document_storage
from app.storage.local import LocalDocumentStorage


def test_upload_pdf_records_metadata_and_stores_content(tmp_path) -> None:
    storage = LocalDocumentStorage(root=tmp_path)
    app.dependency_overrides[get_document_storage] = lambda: storage

    try:
        with TestClient(app) as client:
            bundle_response = client.post(
                "/bundles",
                json={"tenant_id": "upload-test"},
            )
            bundle_id = bundle_response.json()["id"]

            upload_response = client.post(
                f"/bundles/{bundle_id}/documents",
                files={
                    "file": (
                        "invoice.pdf",
                        b"%PDF-1.7 example invoice",
                        "application/pdf",
                    ),
                },
            )
    finally:
        app.dependency_overrides.clear()

    payload = upload_response.json()

    assert bundle_response.status_code == 201
    assert upload_response.status_code == 201
    assert payload["bundle_id"] == bundle_id
    assert payload["document_type"] == "unknown"
    assert payload["original_filename"] == "invoice.pdf"
    assert payload["content_type"] == "application/pdf"
    assert payload["size_bytes"] == len(b"%PDF-1.7 example invoice")
    assert len(payload["sha256"]) == 64
    assert payload["processing_status"] == "queued"
    assert (tmp_path / bundle_id / payload["id"] / "invoice.pdf").read_bytes() == (
        b"%PDF-1.7 example invoice"
    )


def test_upload_rejects_content_without_pdf_signature(tmp_path) -> None:
    storage = LocalDocumentStorage(root=tmp_path)
    app.dependency_overrides[get_document_storage] = lambda: storage

    try:
        with TestClient(app) as client:
            bundle_response = client.post(
                "/bundles",
                json={"tenant_id": "upload-test"},
            )
            bundle_id = bundle_response.json()["id"]

            upload_response = client.post(
                f"/bundles/{bundle_id}/documents",
                files={
                    "file": (
                        "invoice.pdf",
                        b"not a PDF",
                        "application/pdf",
                    ),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert bundle_response.status_code == 201
    assert upload_response.status_code == 422
    assert upload_response.json() == {
        "detail": "The file does not have a valid PDF signature.",
    }
    assert not any(tmp_path.iterdir())


def test_duplicate_upload_is_rejected_without_leaving_a_second_file(tmp_path) -> None:
    storage = LocalDocumentStorage(root=tmp_path)
    app.dependency_overrides[get_document_storage] = lambda: storage
    content = b"%PDF-1.7 duplicate invoice"

    try:
        with TestClient(app) as client:
            bundle_response = client.post(
                "/bundles",
                json={"tenant_id": "upload-test"},
            )
            bundle_id = bundle_response.json()["id"]

            first_upload = client.post(
                f"/bundles/{bundle_id}/documents",
                files={"file": ("invoice.pdf", content, "application/pdf")},
            )
            duplicate_upload = client.post(
                f"/bundles/{bundle_id}/documents",
                files={"file": ("invoice-copy.pdf", content, "application/pdf")},
            )
    finally:
        app.dependency_overrides.clear()

    stored_files = [path for path in tmp_path.rglob("*") if path.is_file()]

    assert bundle_response.status_code == 201
    assert first_upload.status_code == 201
    assert duplicate_upload.status_code == 409
    assert duplicate_upload.json() == {
        "detail": "This document already exists in the bundle.",
    }
    assert len(stored_files) == 1


def test_upload_to_unknown_bundle_does_not_write_a_file(tmp_path) -> None:
    storage = LocalDocumentStorage(root=tmp_path)
    app.dependency_overrides[get_document_storage] = lambda: storage

    try:
        with TestClient(app) as client:
            upload_response = client.post(
                f"/bundles/{uuid4()}/documents",
                files={
                    "file": (
                        "invoice.pdf",
                        b"%PDF-1.7 unknown bundle",
                        "application/pdf",
                    ),
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert upload_response.status_code == 404
    assert upload_response.json() == {
        "detail": "Document bundle was not found.",
    }
    assert not any(tmp_path.iterdir())
