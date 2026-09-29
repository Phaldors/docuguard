from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.document import Document
from app.models.processing_job import DocumentProcessingJob


class ProcessingJobNotFoundError(Exception):
    """Raised when a processing job cannot be found."""


class InvalidProcessingJobStateError(Exception):
    """Raised when a job transition is not valid for its current state."""


async def claim_next_processing_job(
    *,
    session: AsyncSession,
) -> DocumentProcessingJob | None:
    job = await session.scalar(
        select(DocumentProcessingJob)
        .where(
            DocumentProcessingJob.status == "queued",
            DocumentProcessingJob.available_at <= datetime.now(UTC),
        )
        .order_by(
            DocumentProcessingJob.available_at,
            DocumentProcessingJob.created_at,
        )
        .limit(1)
        .with_for_update(skip_locked=True)
    )

    if job is None:
        return None

    document = await session.get(Document, job.document_id)
    if document is None:
        raise RuntimeError("Processing job references a missing document.")

    job.status = "running"
    job.attempts += 1
    job.locked_at = datetime.now(UTC)
    document.processing_status = "processing"

    await session.flush()
    return job


async def mark_processing_job_succeeded(
    *,
    session: AsyncSession,
    job_id: UUID,
    document_status: str = "processed",
) -> DocumentProcessingJob:
    job = await _get_running_job(session=session, job_id=job_id)
    document = await session.get(Document, job.document_id)
    if document is None:
        raise RuntimeError("Processing job references a missing document.")

    job.status = "succeeded"
    job.completed_at = datetime.now(UTC)
    job.locked_at = None
    document.processing_status = document_status

    await session.flush()
    return job


async def handle_processing_job_failure(
    *,
    session: AsyncSession,
    job_id: UUID,
    error_message: str,
    max_attempts: int = 3,
    retry_delay: timedelta = timedelta(minutes=1),
) -> DocumentProcessingJob:
    if max_attempts < 1:
        raise ValueError("max_attempts must be at least 1.")

    job = await _get_running_job(session=session, job_id=job_id)
    document = await session.get(Document, job.document_id)
    if document is None:
        raise RuntimeError("Processing job references a missing document.")

    job.last_error = error_message
    job.locked_at = None

    if job.attempts >= max_attempts:
        job.status = "failed"
        job.completed_at = datetime.now(UTC)
        document.processing_status = "failed"
    else:
        job.status = "queued"
        job.available_at = datetime.now(UTC) + retry_delay
        document.processing_status = "queued"

    await session.flush()
    return job


async def _get_running_job(
    *,
    session: AsyncSession,
    job_id: UUID,
) -> DocumentProcessingJob:
    job = await session.get(DocumentProcessingJob, job_id, with_for_update=True)

    if job is None:
        raise ProcessingJobNotFoundError
    if job.status != "running":
        raise InvalidProcessingJobStateError

    return job
