from uuid import uuid4

from app.extraction.structured import DocumentFields, ExtractedField
from app.reconciliation.rules import BundleDocument, DiscrepancyType, evaluate_bundle


def field(value: str | None, confidence: float = 0.95) -> ExtractedField:
    return ExtractedField(
        value=value,
        evidence=value,
        confidence=confidence if value is not None else 0.0,
    )


def make_fields(
    *,
    document_type: str = "invoice",
    supplier_name: str | None = "Northwind Ltd.",
    document_number: str | None = "INV-1001",
    document_date: str | None = "2026-09-01",
    currency: str | None = "USD",
    total: str | None = "1,240.00",
    total_confidence: float = 0.95,
) -> DocumentFields:
    return DocumentFields(
        document_type=document_type,
        supplier_name=field(supplier_name),
        document_number=field(document_number),
        document_date=field(document_date),
        currency=field(currency),
        total=field(total, confidence=total_confidence),
    )


def test_a_clean_matching_bundle_has_no_discrepancies() -> None:
    invoice = BundleDocument(document_id=uuid4(), fields=make_fields())
    purchase_order = BundleDocument(
        document_id=uuid4(),
        fields=make_fields(document_type="purchase_order", total="1240.00"),
    )

    discrepancies = evaluate_bundle([invoice, purchase_order])

    assert discrepancies == []


def test_formatting_variance_in_total_is_not_a_mismatch() -> None:
    invoice = BundleDocument(document_id=uuid4(), fields=make_fields(total="1,240.00"))
    purchase_order = BundleDocument(
        document_id=uuid4(),
        fields=make_fields(document_type="purchase_order", total="1240.00"),
    )

    discrepancies = evaluate_bundle([invoice, purchase_order])

    assert discrepancies == []


def test_a_genuine_total_mismatch_is_flagged_as_critical() -> None:
    invoice = BundleDocument(document_id=uuid4(), fields=make_fields(total="1240.00"))
    purchase_order = BundleDocument(
        document_id=uuid4(),
        fields=make_fields(document_type="purchase_order", total="1300.00"),
    )

    discrepancies = evaluate_bundle([invoice, purchase_order])

    assert len(discrepancies) == 1
    assert discrepancies[0].discrepancy_type == DiscrepancyType.TOTAL_MISMATCH
    assert discrepancies[0].severity == "critical"
    assert discrepancies[0].message.endswith("1240.00, 1300.00.")


def test_supplier_name_case_and_whitespace_variance_is_not_a_mismatch() -> None:
    invoice = BundleDocument(
        document_id=uuid4(), fields=make_fields(supplier_name="Northwind Ltd.")
    )
    delivery_note = BundleDocument(
        document_id=uuid4(),
        fields=make_fields(
            document_type="delivery_note",
            supplier_name="  northwind ltd.  ",
            total=None,
        ),
    )

    discrepancies = evaluate_bundle([invoice, delivery_note])

    assert discrepancies == []


def test_a_supplier_mismatch_is_flagged() -> None:
    invoice = BundleDocument(
        document_id=uuid4(), fields=make_fields(supplier_name="Northwind Ltd.")
    )
    purchase_order = BundleDocument(
        document_id=uuid4(),
        fields=make_fields(document_type="purchase_order", supplier_name="Acme Corp"),
    )

    discrepancies = evaluate_bundle([invoice, purchase_order])

    types = {discrepancy.discrepancy_type for discrepancy in discrepancies}
    assert DiscrepancyType.SUPPLIER_MISMATCH in types


def test_a_missing_required_field_is_flagged() -> None:
    invoice = BundleDocument(document_id=uuid4(), fields=make_fields(total=None))

    discrepancies = evaluate_bundle([invoice])

    assert len(discrepancies) == 1
    assert discrepancies[0].discrepancy_type == DiscrepancyType.MISSING_REQUIRED_FIELD


def test_a_low_confidence_required_field_is_flagged_as_advisory() -> None:
    invoice = BundleDocument(
        document_id=uuid4(), fields=make_fields(total="1240.00", total_confidence=0.4)
    )

    discrepancies = evaluate_bundle([invoice], confidence_threshold=0.7)

    assert len(discrepancies) == 1
    assert discrepancies[0].discrepancy_type == DiscrepancyType.LOW_CONFIDENCE_FIELD
    assert discrepancies[0].severity == "advisory"


def test_an_unclassified_document_type_is_flagged() -> None:
    receipt = BundleDocument(document_id=uuid4(), fields=make_fields(document_type="other"))

    discrepancies = evaluate_bundle([receipt])

    assert len(discrepancies) == 1
    assert discrepancies[0].discrepancy_type == DiscrepancyType.UNCLASSIFIED_DOCUMENT_TYPE


def test_a_document_with_no_extracted_fields_is_flagged() -> None:
    document = BundleDocument(document_id=uuid4(), fields=None)

    discrepancies = evaluate_bundle([document])

    assert len(discrepancies) == 1
    assert discrepancies[0].discrepancy_type == DiscrepancyType.DOCUMENT_NOT_PROCESSED


def test_a_delivery_note_with_no_total_is_not_flagged_as_missing() -> None:
    delivery_note = BundleDocument(
        document_id=uuid4(), fields=make_fields(document_type="delivery_note", total=None)
    )

    discrepancies = evaluate_bundle([delivery_note])

    assert discrepancies == []
