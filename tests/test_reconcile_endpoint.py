import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import session_factory
from app.main import app
from app.models.document import Document
from app.models.document_field_extraction import DocumentFieldExtraction


async def add_extracted_document(
    session, *, bundle_id, document_type: str, total_value: str
) -> None:
    document = Document(
        bundle_id=bundle_id,
        document_type=document_type,
        original_filename=f"{document_type}.pdf",
        content_type="application/pdf",
        size_bytes=10,
        sha256=f"sha-{document_type}-{uuid4().hex}",
        storage_key=f"key-{document_type}-{uuid4().hex}",
        processing_status="extracted",
    )
    session.add(document)
    await session.flush()

    session.add(
        DocumentFieldExtraction(
            document_id=document.id,
            document_type=document_type,
            supplier_name_value="Northwind Ltd.",
            supplier_name_evidence="Northwind Ltd.",
            supplier_name_confidence=0.95,
            document_number_value="REF-1",
            document_number_evidence="REF-1",
            document_number_confidence=0.9,
            document_date_value="2026-09-01",
            document_date_evidence="2026-09-01",
            document_date_confidence=0.9,
            currency_value="USD",
            currency_evidence="USD",
            currency_confidence=0.95,
            total_value=total_value,
            total_evidence=total_value,
            total_confidence=0.95,
        )
    )


def test_reconcile_endpoint_flags_a_mismatch_and_returns_it() -> None:
    tenant_id = f"test-{uuid4().hex}"

    with TestClient(app) as client:
        create_response = client.post("/bundles", json={"tenant_id": tenant_id})
        bundle_id = create_response.json()["id"]

        async def seed() -> None:
            async with session_factory() as session:
                await add_extracted_document(
                    session,
                    bundle_id=bundle_id,
                    document_type="invoice",
                    total_value="1240.00",
                )
                await add_extracted_document(
                    session,
                    bundle_id=bundle_id,
                    document_type="purchase_order",
                    total_value="1300.00",
                )
                await session.commit()

        asyncio.run(seed())

        reconcile_response = client.post(f"/bundles/{bundle_id}/reconcile")

    assert reconcile_response.status_code == 200
    body = reconcile_response.json()
    assert body["bundle"]["status"] == "ready_for_review"
    assert len(body["discrepancies"]) == 1
    assert body["discrepancies"][0]["discrepancy_type"] == "total_mismatch"
    assert body["discrepancies"][0]["severity"] == "critical"


def test_reconcile_endpoint_returns_404_for_an_unknown_bundle() -> None:
    with TestClient(app) as client:
        response = client.post(f"/bundles/{uuid4()}/reconcile")

    assert response.status_code == 404


def test_reconcile_endpoint_returns_409_for_a_bundle_with_no_documents() -> None:
    tenant_id = f"test-{uuid4().hex}"

    with TestClient(app) as client:
        create_response = client.post("/bundles", json={"tenant_id": tenant_id})
        bundle_id = create_response.json()["id"]

        response = client.post(f"/bundles/{bundle_id}/reconcile")

    assert response.status_code == 409
