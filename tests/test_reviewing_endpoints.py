import asyncio
from uuid import uuid4

from fastapi.testclient import TestClient

from app.db.session import session_factory
from app.main import app
from app.models.document import Document
from app.models.document_field_extraction import DocumentFieldExtraction


async def seed_extracted_document(bundle_id: str) -> str:
    async with session_factory() as session:
        document = Document(
            bundle_id=bundle_id,
            document_type="invoice",
            original_filename="invoice.pdf",
            content_type="application/pdf",
            size_bytes=10,
            sha256=f"sha-{uuid4().hex}",
            storage_key=f"key-{uuid4().hex}",
            processing_status="extracted",
        )
        session.add(document)
        await session.flush()

        session.add(
            DocumentFieldExtraction(
                document_id=document.id,
                document_type="invoice",
                supplier_name_value="Northwind Ltd.",
                supplier_name_evidence="Northwind Ltd.",
                supplier_name_confidence=0.95,
                document_number_value="INV-1001",
                document_number_evidence="INV-1001",
                document_number_confidence=0.9,
                document_date_value="2026-09-01",
                document_date_evidence="2026-09-01",
                document_date_confidence=0.9,
                currency_value="USD",
                currency_evidence="USD",
                currency_confidence=0.95,
                total_value="1240.00",
                total_evidence="1240.00",
                total_confidence=0.95,
            )
        )
        await session.commit()
        return str(document.id)


def test_reviewer_queue_lists_only_bundles_ready_for_review() -> None:
    with TestClient(app) as client:
        pending_id = client.post(
            "/bundles", json={"tenant_id": f"queue-test-{uuid4().hex}"}
        ).json()["id"]
        ready_id = client.post(
            "/bundles", json={"tenant_id": f"queue-test-{uuid4().hex}"}
        ).json()["id"]

        asyncio.run(seed_extracted_document(ready_id))
        client.post(f"/bundles/{ready_id}/reconcile")

        response = client.get("/bundles", params={"status": "ready_for_review"})

    listed_ids = {bundle["id"] for bundle in response.json()}
    assert ready_id in listed_ids
    assert pending_id not in listed_ids


def test_full_review_flow_correction_then_decision_then_audit_trail() -> None:
    with TestClient(app) as client:
        bundle_id = client.post(
            "/bundles", json={"tenant_id": f"flow-test-{uuid4().hex}"}
        ).json()["id"]
        document_id = asyncio.run(seed_extracted_document(bundle_id))
        client.post(f"/bundles/{bundle_id}/reconcile")

        correction_response = client.post(
            f"/bundles/{bundle_id}/documents/{document_id}/corrections",
            json={
                "field_name": "total",
                "action": "corrected",
                "actor": "reviewer@example.com",
                "new_value": "1300.00",
                "reason": "Extractor misread the total.",
            },
        )
        assert correction_response.status_code == 201
        assert correction_response.json()["action"] == "corrected"

        decision_response = client.post(
            f"/bundles/{bundle_id}/decision",
            json={
                "action": "approved",
                "actor": "reviewer@example.com",
                "reason": "Total corrected and re-checked.",
            },
        )
        assert decision_response.status_code == 200
        assert decision_response.json()["bundle"]["status"] == "approved"

        audit_events_response = client.get(f"/bundles/{bundle_id}/audit-events")

    events = audit_events_response.json()
    assert len(events) == 2
    assert {event["event_type"] for event in events} == {
        "field_correction",
        "case_decision",
    }


def test_a_decision_without_a_reason_is_rejected() -> None:
    with TestClient(app) as client:
        bundle_id = client.post(
            "/bundles", json={"tenant_id": f"no-reason-test-{uuid4().hex}"}
        ).json()["id"]
        asyncio.run(seed_extracted_document(bundle_id))
        client.post(f"/bundles/{bundle_id}/reconcile")

        response = client.post(
            f"/bundles/{bundle_id}/decision",
            json={"action": "approved", "actor": "reviewer@example.com", "reason": ""},
        )

    assert response.status_code == 422


def test_a_decision_on_a_bundle_not_ready_for_review_is_rejected() -> None:
    with TestClient(app) as client:
        bundle_id = client.post(
            "/bundles", json={"tenant_id": f"not-ready-test-{uuid4().hex}"}
        ).json()["id"]

        response = client.post(
            f"/bundles/{bundle_id}/decision",
            json={
                "action": "approved",
                "actor": "reviewer@example.com",
                "reason": "Looks fine.",
            },
        )

    assert response.status_code == 409
