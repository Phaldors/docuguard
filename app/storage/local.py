from pathlib import Path
from uuid import UUID

from app.storage.base import DocumentStorage


class LocalDocumentStorage(DocumentStorage):
    def __init__(self, root: Path) -> None:
        self.root = root

    def save(
        self,
        *,
        bundle_id: UUID,
        document_id: UUID,
        filename: str,
        content: bytes,
    ) -> str:
        safe_filename = Path(filename).name

        if safe_filename != filename or "\\" in filename:
            raise ValueError("The filename must not contain a path.")

        destination = self.root / str(bundle_id) / str(document_id) / safe_filename
        destination.parent.mkdir(parents=True, exist_ok=True)

        temporary_destination = destination.with_suffix(
            f"{destination.suffix}.tmp",
        )
        temporary_destination.write_bytes(content)
        temporary_destination.replace(destination)

        return destination.relative_to(self.root).as_posix()

    def delete(self, *, key: str) -> None:
        self._resolve_key(key).unlink(missing_ok=True)

    def read(self, *, key: str) -> bytes:
        return self._resolve_key(key).read_bytes()

    def _resolve_key(self, key: str) -> Path:
        root = self.root.resolve()
        path = (root / key).resolve()

        try:
            path.relative_to(root)
        except ValueError as error:
            raise ValueError("The path is outside the storage root.") from error

        return path
