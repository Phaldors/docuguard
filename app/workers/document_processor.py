from sqlalchemy.ext.asyncio import AsyncSession

from app.extraction.pdf import extract_native_pdf_text
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.services.processing_jobs import (
    claim_next_processing_job,
    handle_processing_job_failure,
    mark_processing_job_succeeded,
)
from app.storage.base import DocumentStorage


async def process_next_document(
    *, session: AsyncSession, storage: DocumentStorage
) -> bool:
    job = await claim_next_processing_job(session=session)
    if job is None:
        return False

    job_id = job.id
    document_id = job.document_id
    await session.commit()

    try:
        document = await session.get(Document, document_id)
        if document is None:
            raise RuntimeError("Processing job references a missing document.")

        result = extract_native_pdf_text(storage.read(key=document.storage_key))
        session.add(
            DocumentExtraction(
                document_id=document.id,
                method="native_text",
                text_content=result.text_content,
                page_count=result.page_count,
                character_count=len(result.text_content),
                requires_ocr=result.requires_ocr,
                quality_status=result.quality_status,
                quality_note=result.quality_note,
            )
        )
        await mark_processing_job_succeeded(
            session=session,
            job_id=job_id,
            document_status=(
                "needs_ocr"
                if result.requires_ocr
                else "needs_review"
                if result.quality_status == "degraded"
                else "extracted"
            ),
        )
        await session.commit()
    except Exception as error:  # noqa: BLE001
        await session.rollback()
        await handle_processing_job_failure(
            session=session, job_id=job_id, error_message=str(error)
        )
        await session.commit()

    return True
