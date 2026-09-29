import pytest

from app.ingestion.validation import (
    MAX_DOCUMENT_SIZE_BYTES,
    InvalidDocumentError,
    validate_pdf_upload,
)


def test_valid_pdf_upload_is_accepted() -> None:
    validate_pdf_upload(
        filename="invoice.pdf",
        content_type="application/pdf",
        content=b"%PDF-1.7 valid document",
    )


@pytest.mark.parametrize(
    ("filename", "content_type", "content", "message"),
    [
        (
            "invoice.txt",
            "application/pdf",
            b"%PDF-1.7 valid document",
            "Only PDF files are accepted.",
        ),
        (
            "invoice.pdf",
            "text/plain",
            b"%PDF-1.7 valid document",
            "The content type must be application/pdf.",
        ),
        (
            "invoice.pdf",
            "application/pdf",
            b"not actually a PDF",
            "The file does not have a valid PDF signature.",
        ),
        (
            "invoice.pdf",
            "application/pdf",
            b"%PDF-" + b"x" * MAX_DOCUMENT_SIZE_BYTES,
            "The file exceeds the 10 MiB size limit.",
        ),
    ],
)
def test_invalid_pdf_upload_is_rejected(
    filename: str,
    content_type: str,
    content: bytes,
    message: str,
) -> None:
    with pytest.raises(InvalidDocumentError, match=message):
        validate_pdf_upload(
            filename=filename,
            content_type=content_type,
            content=content,
        )
