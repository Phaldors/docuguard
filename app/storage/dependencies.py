from functools import lru_cache

from app.config import get_settings
from app.storage.base import DocumentStorage
from app.storage.local import LocalDocumentStorage


@lru_cache
def get_document_storage() -> DocumentStorage:
    settings = get_settings()

    return LocalDocumentStorage(root=settings.document_storage_path)
