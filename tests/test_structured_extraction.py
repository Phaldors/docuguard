from app.extraction.structured import DocumentFields, ExtractedField


def test_document_fields_schema_forbids_unexpected_properties() -> None:
    schema = DocumentFields.model_json_schema()
    field_schema = ExtractedField.model_json_schema()

    assert schema["additionalProperties"] is False
    assert field_schema["additionalProperties"] is False


def test_document_fields_schema_accepts_evidence_backed_values() -> None:
    extraction = DocumentFields.model_validate(
        {
            "document_type": "invoice",
            "supplier_name": {
                "value": "Northwind Ltd.",
                "evidence": "Supplier: Northwind Ltd.",
                "confidence": 0.99,
            },
            "document_number": {
                "value": "INV-1001",
                "evidence": "Invoice No: INV-1001",
                "confidence": 0.98,
            },
            "document_date": {
                "value": "2026-09-29",
                "evidence": "Date: 2026-09-29",
                "confidence": 0.95,
            },
            "currency": {
                "value": "USD",
                "evidence": "Currency: USD",
                "confidence": 0.97,
            },
            "total": {
                "value": "1,240.00",
                "evidence": "Total: 1,240.00 USD",
                "confidence": 0.97,
            },
        }
    )

    assert extraction.supplier_name.value == "Northwind Ltd."
    assert extraction.total.evidence == "Total: 1,240.00 USD"
