from datetime import timedelta
from io import BytesIO

import pytest
from pypdf import PdfWriter
from sqlalchemy import select

from app.db.session import session_factory
from app.models.bundle import DocumentBundle
from app.models.document_extraction import DocumentExtraction
from app.models.processing_job import DocumentProcessingJob
from app.services.documents import register_document
from app.services.processing_jobs import (
    claim_next_processing_job,
    handle_processing_job_failure,
    mark_processing_job_succeeded,
)
from app.storage.local import LocalDocumentStorage
from app.workers.document_processor import process_next_document


def create_blank_pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=612, height=792)
    output = BytesIO()
    writer.write(output)
    return output.getvalue()


@pytest.mark.asyncio
async def test_upload_queues_a_durable_extraction_job(tmp_path) -> None:
    storage = LocalDocumentStorage(root=tmp_path)

    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="job-test")
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)

        document = await register_document(
            session=session,
            storage=storage,
            bundle_id=bundle.id,
            filename="invoice.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.7 durable job",
        )
        await session.commit()

        job = await session.scalar(
            select(DocumentProcessingJob).where(
                DocumentProcessingJob.document_id == document.id
            )
        )

    assert job is not None
    assert job.job_type == "extract_document"
    assert job.status == "queued"
    assert job.attempts == 0
    assert job.available_at is not None


@pytest.mark.asyncio
async def test_worker_claims_and_completes_a_processing_job(tmp_path) -> None:
    storage = LocalDocumentStorage(root=tmp_path)

    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="worker-test")
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)

        document = await register_document(
            session=session,
            storage=storage,
            bundle_id=bundle.id,
            filename="invoice.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.7 worker claim",
        )
        await session.commit()

        job = await claim_next_processing_job(session=session)

        assert job is not None
        assert job.status == "running"
        assert job.attempts == 1
        await session.commit()

        completed_job = await mark_processing_job_succeeded(
            session=session,
            job_id=job.id,
        )
        await session.commit()
        await session.refresh(document)

    assert completed_job.status == "succeeded"
    assert completed_job.completed_at is not None
    assert completed_job.locked_at is None
    assert document.processing_status == "processed"


@pytest.mark.asyncio
async def test_worker_retries_then_marks_a_job_as_failed(tmp_path) -> None:
    storage = LocalDocumentStorage(root=tmp_path)

    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="retry-test")
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)

        document = await register_document(
            session=session,
            storage=storage,
            bundle_id=bundle.id,
            filename="invoice.pdf",
            content_type="application/pdf",
            content=b"%PDF-1.7 retry job",
        )
        await session.commit()

        first_claim = await claim_next_processing_job(session=session)
        assert first_claim is not None
        retried_job = await handle_processing_job_failure(
            session=session,
            job_id=first_claim.id,
            error_message="Temporary extractor outage.",
            max_attempts=2,
            retry_delay=timedelta(),
        )
        await session.commit()
        await session.refresh(document)

        assert retried_job.status == "queued"
        assert retried_job.last_error == "Temporary extractor outage."
        assert document.processing_status == "queued"

        second_claim = await claim_next_processing_job(session=session)
        assert second_claim is not None
        failed_job = await handle_processing_job_failure(
            session=session,
            job_id=second_claim.id,
            error_message="Extractor is still unavailable.",
            max_attempts=2,
        )
        await session.commit()
        await session.refresh(document)

    assert failed_job.status == "failed"
    assert failed_job.attempts == 2
    assert failed_job.completed_at is not None
    assert document.processing_status == "failed"


@pytest.mark.asyncio
async def test_worker_persists_empty_native_extraction_for_ocr_fallback(
    tmp_path,
) -> None:
    storage = LocalDocumentStorage(root=tmp_path)

    async with session_factory() as session:
        bundle = DocumentBundle(tenant_id="extraction-test")
        session.add(bundle)
        await session.commit()
        await session.refresh(bundle)

        document = await register_document(
            session=session,
            storage=storage,
            bundle_id=bundle.id,
            filename="scan.pdf",
            content_type="application/pdf",
            content=create_blank_pdf(),
        )
        await session.commit()

        did_process = await process_next_document(
            session=session, storage=storage, structured_extractor=None
        )
        extraction = await session.scalar(
            select(DocumentExtraction).where(
                DocumentExtraction.document_id == document.id
            )
        )
        await session.refresh(document)

    assert did_process is True
    assert extraction is not None
    assert extraction.method == "native_text"
    assert extraction.page_count == 1
    assert extraction.text_content == ""
    assert extraction.character_count == 0
    assert extraction.requires_ocr is True
    assert extraction.quality_status == "ocr_required"
    assert extraction.quality_note is None
    assert document.processing_status == "needs_ocr"
