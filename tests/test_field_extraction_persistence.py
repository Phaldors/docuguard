from io import BytesIO

import pytest
from pypdf import PdfWriter
from pypdf.generic import DictionaryObject, NameObject, StreamObject
from sqlalchemy import select

from app.db.session import session_factory
from app.extraction.structured import DocumentFields, ExtractedField
from app.models.bundle import DocumentBundle
from app.models.document_field_extraction import DocumentFieldExtraction
from app.services.documents import register_document
from app.storage.local import LocalDocumentStorage
from app.workers.document_processor import process_next_document


def create_text_pdf(text: str) -> bytes:
    writer = PdfWriter()
    page = writer.add_blank_page(width=300, height=300)

    stream_obj = StreamObject()
    stream_obj.set_data(f"BT /F1 12 Tf 10 250 Td ({text}) Tj ET".encode())
    stream_ref = writer._add_object(stream_obj)

    font = DictionaryObject()
    font[NameObject("/Type")] = NameObject("/Font")
    font[NameObject("/Subtype")] = NameObject("/Type1")
    font[NameObject("/BaseFont")] = NameObject("/Helvetica")
    font_ref = writer._add_object(font)

    font_dict = DictionaryObject()
    font_dict[NameObject("/F1")] = font_ref
    resources = DictionaryObject()
    resources[NameObject("/Font")] = font_dict

    page[NameObject("/Resources")] = resources
    page[NameObject("/Contents")] = stream_ref

    output = BytesIO()
    writer.write(output)
    return output.getvalue()


class FakeStructuredExtractor:
    def __init__(self, fields: DocumentFields) -> None:
        self.fields = fields
        self.received_text: str | None = None

    async def extract(self, *, document_text: str) -> DocumentFields:
        self.received_text = document_text
        return self.fields


def make_fields(*, total_value: str, total_confidence: float) -> DocumentFields:
    empty = ExtractedField(value=None, evidence=None, confidence=0.0)
    return DocumentFields(
        document_type="invoice",
        supplier_name=empty,
        document_number=empty,
        document_date=empty,
        currency=empty,
        total=ExtractedField(
            value=total_value,
            evidence=f"Total: {total_value}",
            confidence=total_confidence,
        ),
    )


@pytest.mark.asyncio
async def test_worker_persists_structured_fields_when_text_is_usable(
    tmp_path,
) -> None:
    storage = LocalDocumentStorage(root=tmp_path)
    extractor = FakeStructuredExtractor(
        make_fields(total_value="1240.00", total_confidence=0.97)
    )

    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="field-extraction-test")
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)

        document = await register_document(
            session=session,
            storage=storage,
            bundle_id=bundle.id,
            filename="invoice.pdf",
            content_type="application/pdf",
            content=create_text_pdf("Total: 1240.00 USD"),
        )
        await session.commit()

        did_process = await process_next_document(
            session=session, storage=storage, structured_extractor=extractor
        )
        field_extraction = await session.scalar(
            select(DocumentFieldExtraction).where(
                DocumentFieldExtraction.document_id == document.id
            )
        )

    assert did_process is True
    assert extractor.received_text == "Total: 1240.00 USD"
    assert field_extraction is not None
    assert field_extraction.document_type == "invoice"
    assert field_extraction.total_value == "1240.00"
    assert field_extraction.total_evidence == "Total: 1240.00"
    assert field_extraction.total_confidence == 0.97
    assert field_extraction.supplier_name_value is None
    assert field_extraction.supplier_name_confidence == 0.0


@pytest.mark.asyncio
async def test_worker_skips_structured_extraction_without_an_extractor(
    tmp_path,
) -> None:
    storage = LocalDocumentStorage(root=tmp_path)

    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="no-extractor-test")
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)

        document = await register_document(
            session=session,
            storage=storage,
            bundle_id=bundle.id,
            filename="invoice.pdf",
            content_type="application/pdf",
            content=create_text_pdf("Total: 500.00 USD"),
        )
        await session.commit()

        did_process = await process_next_document(
            session=session, storage=storage, structured_extractor=None
        )
        field_extraction = await session.scalar(
            select(DocumentFieldExtraction).where(
                DocumentFieldExtraction.document_id == document.id
            )
        )

    assert did_process is True
    assert field_extraction is None


@pytest.mark.asyncio
async def test_worker_skips_structured_extraction_when_ocr_is_required(
    tmp_path,
) -> None:
    storage = LocalDocumentStorage(root=tmp_path)
    extractor = FakeStructuredExtractor(
        make_fields(total_value="0.00", total_confidence=0.5)
    )

    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="ocr-required-test")
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)

        blank_writer = PdfWriter()
        blank_writer.add_blank_page(width=300, height=300)
        blank_output = BytesIO()
        blank_writer.write(blank_output)

        document = await register_document(
            session=session,
            storage=storage,
            bundle_id=bundle.id,
            filename="scan.pdf",
            content_type="application/pdf",
            content=blank_output.getvalue(),
        )
        await session.commit()

        did_process = await process_next_document(
            session=session, storage=storage, structured_extractor=extractor
        )
        field_extraction = await session.scalar(
            select(DocumentFieldExtraction).where(
                DocumentFieldExtraction.document_id == document.id
            )
        )

    assert did_process is True
    assert extractor.received_text is None
    assert field_extraction is None
