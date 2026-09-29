import argparse
import asyncio
from uuid import UUID

from sqlalchemy import select

from app.config import get_settings
from app.db.session import session_factory
from app.extraction.structured import StructuredDocumentExtractor
from app.models.document_extraction import DocumentExtraction


async def main(document_id: UUID) -> None:
    settings = get_settings()
    if settings.openai_api_key is None:
        raise RuntimeError("DOCUGUARD_OPENAI_API_KEY is required.")

    async with session_factory() as session:
        extraction = await session.scalar(
            select(DocumentExtraction)
            .where(DocumentExtraction.document_id == document_id)
            .order_by(DocumentExtraction.created_at.desc())
        )

    if extraction is None:
        raise RuntimeError("No extracted text exists for this document.")

    extractor = StructuredDocumentExtractor(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.extraction_model,
    )
    fields = await extractor.extract(document_text=extraction.text_content)
    print(fields.model_dump_json(indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("document_id", type=UUID)
    arguments = parser.parse_args()
    asyncio.run(main(arguments.document_id))
