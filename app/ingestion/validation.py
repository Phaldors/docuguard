MAX_DOCUMENT_SIZE_BYTES = 10 * 1024 * 1024
PDF_SIGNATURE = b"%PDF-"


class InvalidDocumentError(ValueError):
    pass


def validate_pdf_upload(
    *,
    filename: str,
    content_type: str | None,
    content: bytes,
) -> None:
    if not filename.lower().endswith(".pdf"):
        raise InvalidDocumentError("Only PDF files are accepted.")

    if content_type != "application/pdf":
        raise InvalidDocumentError("The content type must be application/pdf.")

    if not content.startswith(PDF_SIGNATURE):
        raise InvalidDocumentError("The file does not have a valid PDF signature.")

    if len(content) > MAX_DOCUMENT_SIZE_BYTES:
        raise InvalidDocumentError("The file exceeds the 10 MiB size limit.")
