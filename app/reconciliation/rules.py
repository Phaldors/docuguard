"""Deterministic reconciliation rules for documents within a bundle.

Per docs/data-contract.md, the full reconciliation truth-case taxonomy also
includes a document-number cross-reference mismatch, a date-outside-window
mismatch, and a quantity/missing-line-item mismatch. Those require schema
fields DocuGuard does not extract yet -- a cross-document reference number,
a normalised date, and line_items -- and are deferred rather than
approximated with fragile guessing. What is implemented here only compares
fields the extraction system already persists (see
app/models/document_field_extraction.py).
"""

import re
from collections.abc import Callable
from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID

from app.extraction.structured import DocumentFields


class DiscrepancyType(StrEnum):
    DOCUMENT_NOT_PROCESSED = "document_not_processed"
    UNCLASSIFIED_DOCUMENT_TYPE = "unclassified_document_type"
    MISSING_REQUIRED_FIELD = "missing_required_field"
    LOW_CONFIDENCE_FIELD = "low_confidence_field"
    TOTAL_MISMATCH = "total_mismatch"
    SUPPLIER_MISMATCH = "supplier_mismatch"
    CURRENCY_MISMATCH = "currency_mismatch"


class Severity(StrEnum):
    CRITICAL = "critical"
    ADVISORY = "advisory"


SEVERITY_BY_TYPE: dict[DiscrepancyType, Severity] = {
    DiscrepancyType.DOCUMENT_NOT_PROCESSED: Severity.CRITICAL,
    DiscrepancyType.UNCLASSIFIED_DOCUMENT_TYPE: Severity.CRITICAL,
    DiscrepancyType.MISSING_REQUIRED_FIELD: Severity.CRITICAL,
    DiscrepancyType.LOW_CONFIDENCE_FIELD: Severity.ADVISORY,
    DiscrepancyType.TOTAL_MISMATCH: Severity.CRITICAL,
    DiscrepancyType.SUPPLIER_MISMATCH: Severity.CRITICAL,
    DiscrepancyType.CURRENCY_MISMATCH: Severity.CRITICAL,
}

# A document type absent from this map is treated as UNCLASSIFIED_DOCUMENT_TYPE.
# Delivery notes have no required total: they confirm goods shipped, not price.
REQUIRED_FIELDS_BY_DOCUMENT_TYPE: dict[str, tuple[str, ...]] = {
    "invoice": ("supplier_name", "total"),
    "purchase_order": ("supplier_name", "total"),
    "delivery_note": ("supplier_name",),
}


@dataclass(frozen=True)
class BundleDocument:
    document_id: UUID
    fields: DocumentFields | None


@dataclass(frozen=True)
class Discrepancy:
    discrepancy_type: DiscrepancyType
    severity: Severity
    message: str
    document_ids: tuple[UUID, ...]


def evaluate_bundle(
    documents: list[BundleDocument], *, confidence_threshold: float = 0.7
) -> list[Discrepancy]:
    discrepancies: list[Discrepancy] = []

    for document in documents:
        discrepancies.extend(_check_document(document, confidence_threshold))

    extracted = [document for document in documents if document.fields is not None]
    discrepancies.extend(
        _check_cross_document_agreement(
            extracted, "total", DiscrepancyType.TOTAL_MISMATCH, _normalize_amount
        )
    )
    discrepancies.extend(
        _check_cross_document_agreement(
            extracted,
            "supplier_name",
            DiscrepancyType.SUPPLIER_MISMATCH,
            _normalize_text,
        )
    )
    discrepancies.extend(
        _check_cross_document_agreement(
            extracted, "currency", DiscrepancyType.CURRENCY_MISMATCH, _normalize_text
        )
    )

    return discrepancies


def _check_document(
    document: BundleDocument, confidence_threshold: float
) -> list[Discrepancy]:
    if document.fields is None:
        return [
            _discrepancy(
                DiscrepancyType.DOCUMENT_NOT_PROCESSED,
                "Document has no extracted fields yet.",
                (document.document_id,),
            )
        ]

    fields = document.fields
    required_fields = REQUIRED_FIELDS_BY_DOCUMENT_TYPE.get(fields.document_type)
    if required_fields is None:
        return [
            _discrepancy(
                DiscrepancyType.UNCLASSIFIED_DOCUMENT_TYPE,
                f"Document type '{fields.document_type}' is not a recognised "
                "invoice, purchase_order, or delivery_note.",
                (document.document_id,),
            )
        ]

    found: list[Discrepancy] = []
    for field_name in required_fields:
        extracted_field = getattr(fields, field_name)
        if extracted_field.value is None:
            found.append(
                _discrepancy(
                    DiscrepancyType.MISSING_REQUIRED_FIELD,
                    f"Required field '{field_name}' is missing on this "
                    f"{fields.document_type}.",
                    (document.document_id,),
                )
            )
        elif extracted_field.confidence < confidence_threshold:
            found.append(
                _discrepancy(
                    DiscrepancyType.LOW_CONFIDENCE_FIELD,
                    f"Field '{field_name}' was extracted at confidence "
                    f"{extracted_field.confidence:.2f}, below the "
                    f"{confidence_threshold:.2f} review threshold.",
                    (document.document_id,),
                )
            )
    return found


def _check_cross_document_agreement(
    documents: list[BundleDocument],
    field_name: str,
    discrepancy_type: DiscrepancyType,
    normalize: Callable[[str], str | None],
) -> list[Discrepancy]:
    present: list[tuple[BundleDocument, str, str]] = []
    for document in documents:
        raw_value = getattr(document.fields, field_name).value
        if raw_value is None:
            continue
        normalized_value = normalize(raw_value)
        if normalized_value is not None:
            present.append((document, raw_value, normalized_value))
    if len(present) < 2:
        return []

    distinct_normalized_values = sorted({normalized for _, _, normalized in present})
    if len(distinct_normalized_values) <= 1:
        return []

    # Normalised values decide equality; raw values are the evidence a reviewer
    # needs to understand the discrepancy. Never expose an internal comparison
    # token such as "124000" as if it were the extracted total.
    display_value_by_normalized = {
        normalized: raw for _, raw, normalized in present
    }
    display_values = [
        display_value_by_normalized[value] for value in distinct_normalized_values
    ]

    return [
        _discrepancy(
            discrepancy_type,
            f"'{field_name}' disagrees across the bundle: "
            f"{', '.join(display_values)}.",
            tuple(document.document_id for document, _, _ in present),
        )
    ]


def _discrepancy(
    discrepancy_type: DiscrepancyType, message: str, document_ids: tuple[UUID, ...]
) -> Discrepancy:
    return Discrepancy(
        discrepancy_type=discrepancy_type,
        severity=SEVERITY_BY_TYPE[discrepancy_type],
        message=message,
        document_ids=document_ids,
    )


def _normalize_amount(value: str) -> str | None:
    digits = re.sub(r"[^0-9]", "", value)
    return digits or None


def _normalize_text(value: str) -> str | None:
    normalized = value.strip().casefold()
    return normalized or None
