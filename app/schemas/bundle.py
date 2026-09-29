from pydantic import BaseModel, ConfigDict, Field


class CreateDocumentBundleRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    tenant_id: str = Field(min_length=1, max_length=64)


from datetime import datetime
from uuid import UUID


class DocumentBundleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    tenant_id: str
    status: str
    created_at: datetime


class DocumentResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bundle_id: UUID
    document_type: str
    original_filename: str
    content_type: str
    size_bytes: int
    sha256: str
    processing_status: str
    created_at: datetime


class DocumentExtractionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    method: str
    text_content: str
    page_count: int
    character_count: int
    requires_ocr: bool
    quality_status: str
    quality_note: str | None
    created_at: datetime


class DocumentFieldExtractionSummaryResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    document_type: str
    supplier_name_value: str | None
    supplier_name_evidence: str | None
    supplier_name_confidence: float
    document_number_value: str | None
    document_number_evidence: str | None
    document_number_confidence: float
    document_date_value: str | None
    document_date_evidence: str | None
    document_date_confidence: float
    currency_value: str | None
    currency_evidence: str | None
    currency_confidence: float
    total_value: str | None
    total_evidence: str | None
    total_confidence: float
    created_at: datetime


class DocumentDetailResponse(DocumentResponse):
    extraction: DocumentExtractionSummaryResponse | None
    fields: DocumentFieldExtractionSummaryResponse | None


class BundleDiscrepancyResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    discrepancy_type: str
    severity: str
    message: str
    document_ids: list[UUID]
    created_at: datetime


class ReconcileBundleResponse(BaseModel):
    bundle: DocumentBundleResponse
    discrepancies: list[BundleDiscrepancyResponse]


class AuditEventResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    bundle_id: UUID
    document_id: UUID | None
    event_type: str
    action: str
    field_name: str | None
    prior_value: str | None
    new_value: str | None
    actor: str
    reason: str | None
    created_at: datetime


class RecordFieldCorrectionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    field_name: str
    action: str
    actor: str = Field(min_length=1, max_length=128)
    new_value: str | None = None
    reason: str | None = None


class RecordCaseDecisionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    action: str
    actor: str = Field(min_length=1, max_length=128)
    reason: str = Field(min_length=1)


class CaseDecisionResponse(BaseModel):
    bundle: DocumentBundleResponse
    audit_event: AuditEventResponse


class ReviewerCaseResponse(BaseModel):
    """Read model for the human-review screen, never a decision payload."""

    bundle: DocumentBundleResponse
    documents: list[DocumentDetailResponse]
    discrepancies: list[BundleDiscrepancyResponse]
    audit_events: list[AuditEventResponse]
