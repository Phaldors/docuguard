from typing import Protocol
from uuid import UUID


class DocumentStorage(Protocol):
    def save(
        self,
        *,
        bundle_id: UUID,
        document_id: UUID,
        filename: str,
        content: bytes,
    ) -> str: ...

    def read(self, *, key: str) -> bytes: ...

    def delete(self, *, key: str) -> None: ...
