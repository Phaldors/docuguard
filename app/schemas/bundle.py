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
    supplier_name_confidence: float
    document_number_value: str | None
    document_number_confidence: float
    document_date_value: str | None
    document_date_confidence: float
    currency_value: str | None
    currency_confidence: float
    total_value: str | None
    total_confidence: float
    created_at: datetime


class DocumentDetailResponse(DocumentResponse):
    extraction: DocumentExtractionSummaryResponse | None
    fields: DocumentFieldExtractionSummaryResponse | None
