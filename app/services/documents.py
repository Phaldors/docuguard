import hashlib
from uuid import UUID, uuid4

from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.validation import validate_pdf_upload
from app.models.bundle import DocumentBundle
from app.models.document import Document
from app.models.processing_job import DocumentProcessingJob
from app.storage.base import DocumentStorage


class BundleNotFoundError(Exception):
    """Raised when a document is uploaded to an unknown bundle."""


class DuplicateDocumentError(Exception):
    """Raised when a bundle already contains the same document content."""


async def register_document(
    *,
    session: AsyncSession,
    storage: DocumentStorage,
    bundle_id: UUID,
    filename: str,
    content_type: str,
    content: bytes,
) -> Document:
    bundle = await session.get(DocumentBundle, bundle_id)

    if bundle is None:
        raise BundleNotFoundError

    validate_pdf_upload(
        filename=filename,
        content_type=content_type,
        content=content,
    )

    document_id = uuid4()
    storage_key = storage.save(
        bundle_id=bundle_id,
        document_id=document_id,
        filename=filename,
        content=content,
    )

    document = Document(
        id=document_id,
        bundle_id=bundle_id,
        original_filename=filename,
        content_type=content_type,
        size_bytes=len(content),
        sha256=hashlib.sha256(content).hexdigest(),
        storage_key=storage_key,
        processing_status="queued",
    )
    session.add(document)
    session.add(DocumentProcessingJob(document_id=document_id))

    try:
        await session.flush()
        await session.refresh(document)
    except IntegrityError as error:
        storage.delete(key=storage_key)
        raise DuplicateDocumentError from error
    except Exception:
        storage.delete(key=storage_key)
        raise

    return document
