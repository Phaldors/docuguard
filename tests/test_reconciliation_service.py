from uuid import uuid4

import pytest
from sqlalchemy import select

from app.db.session import session_factory
from app.models.bundle import DocumentBundle
from app.models.discrepancy import BundleDiscrepancy
from app.models.document import Document
from app.models.document_field_extraction import DocumentFieldExtraction
from app.reconciliation.rules import DiscrepancyType
from app.services.reconciliation import (
    BundleNotFoundError,
    BundleNotReadyError,
    reconcile_bundle,
)


async def add_extracted_document(
    session,
    *,
    bundle_id,
    document_type: str,
    total_value: str | None,
    supplier_name_value: str = "Northwind Ltd.",
) -> Document:
    document = Document(
        bundle_id=bundle_id,
        document_type=document_type,
        original_filename=f"{document_type}.pdf",
        content_type="application/pdf",
        size_bytes=10,
        sha256=f"sha-{document_type}-{total_value}",
        storage_key=f"key-{document_type}-{total_value}",
        processing_status="extracted",
    )
    session.add(document)
    await session.flush()

    session.add(
        DocumentFieldExtraction(
            document_id=document.id,
            document_type=document_type,
            supplier_name_value=supplier_name_value,
            supplier_name_evidence=supplier_name_value,
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
            total_confidence=0.95 if total_value is not None else 0.0,
        )
    )
    await session.flush()
    return document


@pytest.mark.asyncio
async def test_reconcile_bundle_flags_a_total_mismatch_and_updates_status() -> None:
    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="reconciliation-test")
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)

        await add_extracted_document(
            session, bundle_id=bundle.id, document_type="invoice", total_value="1240.00"
        )
        await add_extracted_document(
            session,
            bundle_id=bundle.id,
            document_type="purchase_order",
            total_value="1300.00",
        )
        await session.commit()

        reconciled_bundle, discrepancies = await reconcile_bundle(
            session=session, bundle_id=bundle.id
        )
        await session.commit()

        persisted = list(
            await session.scalars(
                select(BundleDiscrepancy).where(
                    BundleDiscrepancy.bundle_id == bundle.id
                )
            )
        )

    assert reconciled_bundle.status == "ready_for_review"
    assert len(discrepancies) == 1
    assert discrepancies[0].discrepancy_type == DiscrepancyType.TOTAL_MISMATCH.value
    assert len(persisted) == 1


@pytest.mark.asyncio
async def test_reconcile_bundle_is_clean_for_a_matching_bundle() -> None:
    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="reconciliation-clean-test")
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)

        await add_extracted_document(
            session, bundle_id=bundle.id, document_type="invoice", total_value="1240.00"
        )
        await add_extracted_document(
            session,
            bundle_id=bundle.id,
            document_type="purchase_order",
            total_value="1,240.00",
        )
        await session.commit()

        reconciled_bundle, discrepancies = await reconcile_bundle(
            session=session, bundle_id=bundle.id
        )
        await session.commit()

    assert reconciled_bundle.status == "ready_for_review"
    assert discrepancies == []


@pytest.mark.asyncio
async def test_reconcile_bundle_rejects_a_bundle_still_in_flight() -> None:
    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="reconciliation-in-flight-test")
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)

        document = Document(
            bundle_id=bundle.id,
            original_filename="invoice.pdf",
            content_type="application/pdf",
            size_bytes=10,
            sha256="sha-in-flight",
            storage_key="key-in-flight",
            processing_status="queued",
        )
        session.add(document)
        await session.commit()

        with pytest.raises(BundleNotReadyError):
            await reconcile_bundle(session=session, bundle_id=bundle.id)


@pytest.mark.asyncio
async def test_reconcile_bundle_raises_for_an_unknown_bundle() -> None:
    async with session_factory() as session:
        with pytest.raises(BundleNotFoundError):
            await reconcile_bundle(session=session, bundle_id=uuid4())


@pytest.mark.asyncio
async def test_reconcile_bundle_replaces_prior_discrepancies_on_rerun() -> None:
    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="reconciliation-rerun-test")
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)

        invoice = await add_extracted_document(
            session, bundle_id=bundle.id, document_type="invoice", total_value="1240.00"
        )
        await add_extracted_document(
            session,
            bundle_id=bundle.id,
            document_type="purchase_order",
            total_value="1300.00",
        )
        await session.commit()

        await reconcile_bundle(session=session, bundle_id=bundle.id)
        await session.commit()

        field_extraction = await session.scalar(
            select(DocumentFieldExtraction).where(
                DocumentFieldExtraction.document_id == invoice.id
            )
        )
        field_extraction.total_value = "1300.00"
        field_extraction.total_evidence = "1300.00"
        await session.commit()

        _, discrepancies = await reconcile_bundle(session=session, bundle_id=bundle.id)
        await session.commit()

        persisted = list(
            await session.scalars(
                select(BundleDiscrepancy).where(
                    BundleDiscrepancy.bundle_id == bundle.id
                )
            )
        )

    assert discrepancies == []
    assert persisted == []
