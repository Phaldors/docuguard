from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db_session
from app.models.audit_event import AuditEvent
from app.models.bundle import DocumentBundle
from app.models.document import Document
from app.models.document_extraction import DocumentExtraction
from app.models.document_field_extraction import DocumentFieldExtraction
from app.schemas.bundle import (
    AuditEventResponse,
    BundleDiscrepancyResponse,
    CaseDecisionResponse,
    CreateDocumentBundleRequest,
    DocumentBundleResponse,
    DocumentDetailResponse,
    DocumentExtractionSummaryResponse,
    DocumentFieldExtractionSummaryResponse,
    DocumentResponse,
    ReconcileBundleResponse,
    RecordCaseDecisionRequest,
    RecordFieldCorrectionRequest,
)
from app.services.documents import (
    BundleNotFoundError,
    DuplicateDocumentError,
    register_document,
)
from app.services.reconciliation import (
    BundleNotFoundError as BundleNotFoundForReconciliationError,
)
from app.services.reconciliation import BundleNotReadyError, reconcile_bundle
from app.services.reviewing import BundleNotFoundError as BundleNotFoundForReviewingError
from app.services.reviewing import (
    DocumentNotFoundError,
    InvalidActionError,
    InvalidBundleStateError,
    UnknownFieldError,
    record_case_decision,
    record_field_correction,
)
from app.storage.base import DocumentStorage
from app.storage.dependencies import get_document_storage

router = APIRouter(prefix="/bundles", tags=["bundles"])


@router.post(
    "",
    response_model=DocumentBundleResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_bundle(
    payload: CreateDocumentBundleRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentBundleResponse:
    bundle = DocumentBundle(tenant_id=payload.tenant_id)

    session.add(bundle)
    await session.flush()
    await session.refresh(bundle)

    return DocumentBundleResponse.model_validate(bundle)


@router.get(
    "",
    response_model=list[DocumentBundleResponse],
)
async def list_bundles(
    session: Annotated[AsyncSession, Depends(get_db_session)],
    status_filter: Annotated[str | None, Query(alias="status")] = None,
) -> list[DocumentBundleResponse]:
    query = select(DocumentBundle).order_by(DocumentBundle.created_at)
    if status_filter is not None:
        query = query.where(DocumentBundle.status == status_filter)

    bundles = await session.scalars(query)
    return [DocumentBundleResponse.model_validate(bundle) for bundle in bundles]


@router.get(
    "/{bundle_id}",
    response_model=DocumentBundleResponse,
)
async def get_bundle(
    bundle_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentBundleResponse:
    bundle = await session.get(DocumentBundle, bundle_id)

    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document bundle was not found.",
        )

    return DocumentBundleResponse.model_validate(bundle)


@router.post(
    "/{bundle_id}/documents",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
)
async def upload_document(
    bundle_id: UUID,
    file: Annotated[UploadFile, File()],
    session: Annotated[AsyncSession, Depends(get_db_session)],
    storage: Annotated[DocumentStorage, Depends(get_document_storage)],
) -> DocumentResponse:
    if file.filename is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail="A filename is required.",
        )

    content = await file.read()

    try:
        document = await register_document(
            session=session,
            storage=storage,
            bundle_id=bundle_id,
            filename=file.filename,
            content_type=file.content_type or "",
            content=content,
        )
    except BundleNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document bundle was not found.",
        ) from None
    except DuplicateDocumentError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="This document already exists in the bundle.",
        ) from None
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return DocumentResponse.model_validate(document)


@router.get(
    "/{bundle_id}/documents/{document_id}",
    response_model=DocumentDetailResponse,
)
async def get_document(
    bundle_id: UUID,
    document_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> DocumentDetailResponse:
    document = await session.scalar(
        select(Document).where(
            Document.id == document_id,
            Document.bundle_id == bundle_id,
        )
    )

    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document was not found.",
        )

    extraction = await session.scalar(
        select(DocumentExtraction).where(
            DocumentExtraction.document_id == document.id,
        )
    )
    field_extraction = await session.scalar(
        select(DocumentFieldExtraction).where(
            DocumentFieldExtraction.document_id == document.id,
        )
    )
    return DocumentDetailResponse(
        **DocumentResponse.model_validate(document).model_dump(),
        extraction=(
            DocumentExtractionSummaryResponse.model_validate(extraction)
            if extraction is not None
            else None
        ),
        fields=(
            DocumentFieldExtractionSummaryResponse.model_validate(field_extraction)
            if field_extraction is not None
            else None
        ),
    )


@router.post(
    "/{bundle_id}/reconcile",
    response_model=ReconcileBundleResponse,
)
async def reconcile_bundle_route(
    bundle_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> ReconcileBundleResponse:
    try:
        bundle, discrepancies = await reconcile_bundle(
            session=session, bundle_id=bundle_id
        )
    except BundleNotFoundForReconciliationError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document bundle was not found.",
        ) from None
    except BundleNotReadyError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return ReconcileBundleResponse(
        bundle=DocumentBundleResponse.model_validate(bundle),
        discrepancies=[
            BundleDiscrepancyResponse.model_validate(discrepancy)
            for discrepancy in discrepancies
        ],
    )


@router.get(
    "/{bundle_id}/audit-events",
    response_model=list[AuditEventResponse],
)
async def list_audit_events(
    bundle_id: UUID,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> list[AuditEventResponse]:
    bundle = await session.get(DocumentBundle, bundle_id)
    if bundle is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document bundle was not found.",
        )

    events = await session.scalars(
        select(AuditEvent)
        .where(AuditEvent.bundle_id == bundle_id)
        .order_by(AuditEvent.created_at)
    )
    return [AuditEventResponse.model_validate(event) for event in events]


@router.post(
    "/{bundle_id}/documents/{document_id}/corrections",
    response_model=AuditEventResponse,
    status_code=status.HTTP_201_CREATED,
)
async def record_field_correction_route(
    bundle_id: UUID,
    document_id: UUID,
    payload: RecordFieldCorrectionRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> AuditEventResponse:
    try:
        event = await record_field_correction(
            session=session,
            bundle_id=bundle_id,
            document_id=document_id,
            field_name=payload.field_name,
            action=payload.action,
            actor=payload.actor,
            new_value=payload.new_value,
            reason=payload.reason,
        )
    except DocumentNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document was not found in this bundle.",
        ) from None
    except (UnknownFieldError, InvalidActionError) as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error

    return AuditEventResponse.model_validate(event)


@router.post(
    "/{bundle_id}/decision",
    response_model=CaseDecisionResponse,
)
async def record_case_decision_route(
    bundle_id: UUID,
    payload: RecordCaseDecisionRequest,
    session: Annotated[AsyncSession, Depends(get_db_session)],
) -> CaseDecisionResponse:
    try:
        bundle, event = await record_case_decision(
            session=session,
            bundle_id=bundle_id,
            action=payload.action,
            actor=payload.actor,
            reason=payload.reason,
        )
    except BundleNotFoundForReviewingError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document bundle was not found.",
        ) from None
    except InvalidActionError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            detail=str(error),
        ) from error
    except InvalidBundleStateError as error:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(error),
        ) from error

    return CaseDecisionResponse(
        bundle=DocumentBundleResponse.model_validate(bundle),
        audit_event=AuditEventResponse.model_validate(event),
    )
