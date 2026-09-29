from functools import lru_cache

from app.config import get_settings
from app.extraction.structured import StructuredDocumentExtractor, StructuredExtractor


@lru_cache
def get_structured_extractor() -> StructuredExtractor | None:
    settings = get_settings()
    if settings.openai_api_key is None:
        return None

    return StructuredDocumentExtractor(
        api_key=settings.openai_api_key.get_secret_value(),
        model=settings.extraction_model,
    )
