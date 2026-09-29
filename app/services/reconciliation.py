from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.extraction.structured import DocumentFields, ExtractedField
from app.models.bundle import DocumentBundle
from app.models.discrepancy import BundleDiscrepancy
from app.models.document import Document
from app.models.document_field_extraction import DocumentFieldExtraction
from app.reconciliation.rules import BundleDocument, evaluate_bundle

# A document still in one of these states has not finished the ingestion
# pipeline; reconciling it now would report it as DOCUMENT_NOT_PROCESSED
# even though it may still succeed on its own.
IN_FLIGHT_STATUSES = {"queued", "processing"}


class BundleNotFoundError(Exception):
    """Raised when a bundle cannot be found."""


class BundleNotReadyError(Exception):
    """Raised when a bundle has no documents or still has documents in flight."""


async def reconcile_bundle(
    *, session: AsyncSession, bundle_id: UUID, confidence_threshold: float = 0.7
) -> tuple[DocumentBundle, list[BundleDiscrepancy]]:
    bundle = await session.get(DocumentBundle, bundle_id)
    if bundle is None:
        raise BundleNotFoundError

    documents = list(
        await session.scalars(
            select(Document).where(Document.bundle_id == bundle_id)
        )
    )
    if not documents:
        raise BundleNotReadyError("Bundle has no documents to reconcile.")
    if any(document.processing_status in IN_FLIGHT_STATUSES for document in documents):
        raise BundleNotReadyError("Not all documents have finished processing.")

    field_rows = {
        row.document_id: row
        for row in await session.scalars(
            select(DocumentFieldExtraction).where(
                DocumentFieldExtraction.document_id.in_(
                    [document.id for document in documents]
                )
            )
        )
    }

    bundle_documents = [
        BundleDocument(
            document_id=document.id,
            fields=(
                _to_document_fields(field_rows[document.id])
                if document.id in field_rows
                else None
            ),
        )
        for document in documents
    ]

    discrepancies = evaluate_bundle(
        bundle_documents, confidence_threshold=confidence_threshold
    )

    # Reconciliation is re-run in full each time (no correction workflow
    # exists yet to make partial re-evaluation meaningful), so the previous
    # result set is replaced rather than accumulated.
    await session.execute(
        delete(BundleDiscrepancy).where(BundleDiscrepancy.bundle_id == bundle_id)
    )
    persisted = [
        BundleDiscrepancy(
            bundle_id=bundle_id,
            discrepancy_type=discrepancy.discrepancy_type.value,
            severity=discrepancy.severity.value,
            message=discrepancy.message,
            document_ids=list(discrepancy.document_ids),
        )
        for discrepancy in discrepancies
    ]
    session.add_all(persisted)

    bundle.status = "ready_for_review"

    await session.flush()
    return bundle, persisted


def _to_document_fields(row: DocumentFieldExtraction) -> DocumentFields:
    return DocumentFields(
        document_type=row.document_type,
        supplier_name=ExtractedField(
            value=row.supplier_name_value,
            evidence=row.supplier_name_evidence,
            confidence=row.supplier_name_confidence,
        ),
        document_number=ExtractedField(
            value=row.document_number_value,
            evidence=row.document_number_evidence,
            confidence=row.document_number_confidence,
        ),
        document_date=ExtractedField(
            value=row.document_date_value,
            evidence=row.document_date_evidence,
            confidence=row.document_date_confidence,
        ),
        currency=ExtractedField(
            value=row.currency_value,
            evidence=row.currency_evidence,
            confidence=row.currency_confidence,
        ),
        total=ExtractedField(
            value=row.total_value,
            evidence=row.total_evidence,
            confidence=row.total_confidence,
        ),
    )
