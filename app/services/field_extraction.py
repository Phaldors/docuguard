from uuid import UUID

from app.extraction.structured import DocumentFields
from app.models.document_field_extraction import DocumentFieldExtraction


def build_document_field_extraction(
    *, document_id: UUID, fields: DocumentFields
) -> DocumentFieldExtraction:
    return DocumentFieldExtraction(
        document_id=document_id,
        document_type=fields.document_type,
        supplier_name_value=fields.supplier_name.value,
        supplier_name_evidence=fields.supplier_name.evidence,
        supplier_name_confidence=fields.supplier_name.confidence,
        document_number_value=fields.document_number.value,
        document_number_evidence=fields.document_number.evidence,
        document_number_confidence=fields.document_number.confidence,
        document_date_value=fields.document_date.value,
        document_date_evidence=fields.document_date.evidence,
        document_date_confidence=fields.document_date.confidence,
        currency_value=fields.currency.value,
        currency_evidence=fields.currency.evidence,
        currency_confidence=fields.currency.confidence,
        total_value=fields.total.value,
        total_evidence=fields.total.evidence,
        total_confidence=fields.total.confidence,
    )
