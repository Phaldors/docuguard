"""Deterministic data for the reviewer-workflow demo.

The fixture deliberately bypasses OCR and LLM extraction. Its purpose is to
make the review and reconciliation flow repeatable without an API key or a
network call. It must never be represented as an extraction-quality dataset.
"""

from dataclasses import dataclass
from hashlib import sha256
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bundle import DocumentBundle
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.models.document_field_extraction import DocumentFieldExtraction
from app.services.reconciliation import reconcile_bundle

DEMO_TENANT_ID = "docuguard-demo"
DEMO_BUNDLE_ID = UUID("d6d48669-9d53-43af-8afb-bd1d7a98c7b6")


@dataclass(frozen=True)
class DemoDocument:
    id: UUID
    document_type: str
    filename: str
    text: str
    supplier_name: str
    supplier_confidence: float
    document_number: str
    document_date: str
    currency: str
    total: str | None
    total_evidence: str | None


DEMO_DOCUMENTS = (
    DemoDocument(
        id=UUID("7089b52c-4c52-42ae-9353-b0ee05f347bb"),
        document_type="invoice",
        filename="northwind-invoice-INV-2026-0042.pdf",
        text=(
            "NORTHWIND INDUSTRIAL LTD.\n"
            "Invoice: INV-2026-0042\n"
            "Date: 2026-09-15\n"
            "Currency: USD\n"
            "Invoice total: 1,240.00 USD\n"
        ),
        supplier_name="Northwind Industrial Ltd.",
        supplier_confidence=0.99,
        document_number="INV-2026-0042",
        document_date="2026-09-15",
        currency="USD",
        total="1240.00",
        total_evidence="1,240.00 USD",
    ),
    DemoDocument(
        id=UUID("0ec01f69-b864-4a14-881a-060443157723"),
        document_type="purchase_order",
        filename="northwind-purchase-order-PO-2026-0917.pdf",
        text=(
            "NORTHWIND INDUSTRIAL LTD.\n"
            "Purchase order: PO-2026-0917\n"
            "Date: 2026-09-10\n"
            "Currency: USD\n"
            "Purchase order total: 1,300.00 USD\n"
        ),
        supplier_name="Northwind Industrial Ltd.",
        supplier_confidence=0.98,
        document_number="PO-2026-0917",
        document_date="2026-09-10",
        currency="USD",
        total="1300.00",
        total_evidence="1,300.00 USD",
    ),
    DemoDocument(
        id=UUID("4e934051-e2ce-4c17-9c09-b8e56bdd9964"),
        document_type="delivery_note",
        filename="northwind-delivery-note-DN-2026-077.pdf",
        text=(
            "Northwind Industrial Ltd.\n"
            "Delivery note: DN-2026-077\n"
            "Date: 2026-09-14\n"
            "Goods received against PO-2026-0917\n"
        ),
        supplier_name="Northwind Industrial Ltd.",
        supplier_confidence=0.62,
        document_number="DN-2026-077",
        document_date="2026-09-14",
        currency="USD",
        total=None,
        total_evidence=None,
    ),
)


async def seed_demo(session: AsyncSession, *, replace: bool = False) -> DocumentBundle:
    """Create the demo case, or return the existing one unless reset is requested."""
    existing = await session.scalar(
        select(DocumentBundle).where(DocumentBundle.id == DEMO_BUNDLE_ID)
    )
    if existing is not None and not replace:
        return existing

    if existing is not None:
        await session.execute(
            delete(DocumentBundle).where(DocumentBundle.id == DEMO_BUNDLE_ID)
        )
        await session.flush()

    bundle = DocumentBundle(
        id=DEMO_BUNDLE_ID,
        tenant_id=DEMO_TENANT_ID,
        status="received",
    )
    session.add(bundle)
    await session.flush()

    for fixture in DEMO_DOCUMENTS:
        encoded_text = fixture.text.encode("utf-8")
        document = Document(
            id=fixture.id,
            bundle_id=bundle.id,
            document_type=fixture.document_type,
            original_filename=fixture.filename,
            content_type="application/pdf",
            size_bytes=len(encoded_text),
            sha256=sha256(encoded_text).hexdigest(),
            storage_key=f"demo-fixtures/{fixture.filename}",
            processing_status="extracted",
        )
        session.add(document)
        session.add(
            DocumentExtraction(
                document_id=document.id,
                method="demo_fixture",
                text_content=fixture.text,
                page_count=1,
                character_count=len(fixture.text),
                requires_ocr=False,
                quality_status="complete",
                quality_note="Synthetic reviewer-workflow fixture.",
            )
        )
        session.add(
            DocumentFieldExtraction(
                document_id=document.id,
                document_type=fixture.document_type,
                supplier_name_value=fixture.supplier_name,
                supplier_name_evidence=fixture.supplier_name,
                supplier_name_confidence=fixture.supplier_confidence,
                document_number_value=fixture.document_number,
                document_number_evidence=fixture.document_number,
                document_number_confidence=0.99,
                document_date_value=fixture.document_date,
                document_date_evidence=fixture.document_date,
                document_date_confidence=0.99,
                currency_value=fixture.currency,
                currency_evidence=fixture.currency,
                currency_confidence=0.99,
                total_value=fixture.total,
                total_evidence=fixture.total_evidence,
                total_confidence=0.99 if fixture.total is not None else 0.0,
            )
        )

    await session.flush()
    reconciled_bundle, _ = await reconcile_bundle(session=session, bundle_id=bundle.id)
    return reconciled_bundle
