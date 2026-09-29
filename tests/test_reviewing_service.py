from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.session import session_factory
from app.models.audit_event import AuditEvent
from app.models.bundle import DocumentBundle
from app.models.document import Document
from app.models.document_field_extraction import DocumentFieldExtraction
from app.services.reviewing import (
    BundleNotFoundError,
    DocumentNotFoundError,
    InvalidActionError,
    InvalidBundleStateError,
    UnknownFieldError,
    record_case_decision,
    record_field_correction,
)


async def make_bundle_with_extracted_document(session, *, status: str = "ready_for_review"):
    bundle = DocumentBundle(tenant_id="reviewing-test", status=status)
    session.add(bundle)
    await session.commit()
    await session.refresh(bundle)

    document = Document(
        bundle_id=bundle.id,
        document_type="invoice",
        original_filename="invoice.pdf",
        content_type="application/pdf",
        size_bytes=10,
        sha256="sha-reviewing-test",
        storage_key="key-reviewing-test",
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
            total_confidence=0.4,
        )
    )
    await session.commit()
    return bundle, document


@pytest.mark.asyncio
async def test_correcting_a_field_appends_an_audit_event_without_touching_the_extraction() -> None:
    async with session_factory() as session:
        bundle, document = await make_bundle_with_extracted_document(session)

        event = await record_field_correction(
            session=session,
            bundle_id=bundle.id,
            document_id=document.id,
            field_name="total",
            action="corrected",
            actor="reviewer@example.com",
            new_value="1300.00",
            reason="Original total misread by the extractor.",
        )
        await session.commit()

        field_extraction = await session.scalar(
            select(DocumentFieldExtraction).where(
                DocumentFieldExtraction.document_id == document.id
            )
        )

    assert event.event_type == "field_correction"
    assert event.action == "corrected"
    assert event.prior_value == "1240.00"
    assert event.new_value == "1300.00"
    assert event.reason == "Original total misread by the extractor."
    # The original extraction is untouched; only the audit trail records the correction.
    assert field_extraction.total_value == "1240.00"


@pytest.mark.asyncio
async def test_keeping_a_field_does_not_require_a_reason() -> None:
    async with session_factory() as session:
        bundle, document = await make_bundle_with_extracted_document(session)

        event = await record_field_correction(
            session=session,
            bundle_id=bundle.id,
            document_id=document.id,
            field_name="total",
            action="kept",
            actor="reviewer@example.com",
        )
        await session.commit()

    assert event.action == "kept"
    assert event.new_value is None


@pytest.mark.asyncio
async def test_marking_a_field_unavailable_requires_a_reason() -> None:
    async with session_factory() as session:
        bundle, document = await make_bundle_with_extracted_document(session)

        with pytest.raises(InvalidActionError):
            await record_field_correction(
                session=session,
                bundle_id=bundle.id,
                document_id=document.id,
                field_name="total",
                action="marked_unavailable",
                actor="reviewer@example.com",
            )


@pytest.mark.asyncio
async def test_correcting_an_unknown_field_is_rejected() -> None:
    async with session_factory() as session:
        bundle, document = await make_bundle_with_extracted_document(session)

        with pytest.raises(UnknownFieldError):
            await record_field_correction(
                session=session,
                bundle_id=bundle.id,
                document_id=document.id,
                field_name="line_items",
                action="kept",
                actor="reviewer@example.com",
            )


@pytest.mark.asyncio
async def test_correcting_a_document_outside_the_bundle_is_rejected() -> None:
    async with session_factory() as session:
        bundle, _document = await make_bundle_with_extracted_document(session)
        _other_bundle, other_document = await make_bundle_with_extracted_document(session)

        with pytest.raises(DocumentNotFoundError):
            await record_field_correction(
                session=session,
                bundle_id=bundle.id,
                document_id=other_document.id,
                field_name="total",
                action="kept",
                actor="reviewer@example.com",
            )


@pytest.mark.asyncio
async def test_case_decision_appends_an_audit_event_and_transitions_the_bundle() -> None:
    async with session_factory() as session:
        bundle, _document = await make_bundle_with_extracted_document(session)

        decided_bundle, event = await record_case_decision(
            session=session,
            bundle_id=bundle.id,
            action="approved",
            actor="reviewer@example.com",
            reason="Discrepancy was reviewed and the total was corrected.",
        )
        await session.commit()

        events = list(
            await session.scalars(
                select(AuditEvent).where(AuditEvent.bundle_id == bundle.id)
            )
        )

    assert decided_bundle.status == "approved"
    assert event.event_type == "case_decision"
    assert event.action == "approved"
    assert event.prior_value == "ready_for_review"
    assert event.new_value == "approved"
    assert len(events) == 1


@pytest.mark.asyncio
async def test_case_decision_requires_a_reason() -> None:
    async with session_factory() as session:
        bundle, _document = await make_bundle_with_extracted_document(session)

        with pytest.raises(InvalidActionError):
            await record_case_decision(
                session=session,
                bundle_id=bundle.id,
                action="approved",
                actor="reviewer@example.com",
                reason="",
            )


@pytest.mark.asyncio
async def test_case_decision_is_rejected_outside_ready_for_review() -> None:
    async with session_factory() as session:
        bundle, _document = await make_bundle_with_extracted_document(
            session, status="received"
        )

        with pytest.raises(InvalidBundleStateError):
            await record_case_decision(
                session=session,
                bundle_id=bundle.id,
                action="approved",
                actor="reviewer@example.com",
                reason="Looks fine.",
            )


@pytest.mark.asyncio
async def test_case_decision_raises_for_an_unknown_bundle() -> None:
    async with session_factory() as session:
        with pytest.raises(BundleNotFoundError):
            await record_case_decision(
                session=session,
                bundle_id=uuid4(),
                action="approved",
                actor="reviewer@example.com",
                reason="N/A",
            )
