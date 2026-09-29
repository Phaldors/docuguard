import logging
from dataclasses import dataclass
from io import BytesIO

from pypdf import PdfReader


@dataclass(frozen=True)
class NativeTextExtraction:
    text_content: str
    page_count: int
    quality_note: str | None = None

    @property
    def requires_ocr(self) -> bool:
        return not self.text_content.strip()

    @property
    def quality_status(self) -> str:
        if self.requires_ocr:
            return "ocr_required"
        if self.quality_note is not None:
            return "degraded"
        return "complete"


class _PypdfWarningCollector(logging.Handler):
    def __init__(self) -> None:
        super().__init__()
        self.messages: list[str] = []

    def emit(self, record: logging.LogRecord) -> None:
        message = record.getMessage()
        if message in {
            "Rotated text discovered. Output will be incomplete.",
            "PDF contains an uninterpretable font. Output will be incomplete.",
        }:
            self.messages.append(message)


def extract_native_pdf_text(content: bytes) -> NativeTextExtraction:
    reader = PdfReader(BytesIO(content), strict=False)
    page_text = []
    warning_collector = _PypdfWarningCollector()
    pypdf_logger = logging.getLogger("pypdf")
    pypdf_logger.addHandler(warning_collector)

    try:
        for page in reader.pages:
            if page.get_contents() is None:
                page_text.append("")
                continue

            page_text.append(page.extract_text(extraction_mode="layout") or "")
    finally:
        pypdf_logger.removeHandler(warning_collector)

    return NativeTextExtraction(
        text_content="\n\n".join(page_text).strip(),
        page_count=len(reader.pages),
        quality_note=" ".join(warning_collector.messages) or None,
    )
