from uuid import uuid4

import pytest

from app.storage.local import LocalDocumentStorage


def test_local_storage_saves_content_under_bundle_directory(tmp_path) -> None:
    storage = LocalDocumentStorage(root=tmp_path)
    bundle_id = uuid4()
    document_id = uuid4()
    content = b"%PDF-1.7 test document"

    storage_key = storage.save(
        bundle_id=bundle_id,
        document_id=document_id,
        filename="invoice.pdf",
        content=content,
    )

    assert storage_key == f"{bundle_id}/{document_id}/invoice.pdf"
    assert (tmp_path / storage_key).read_bytes() == content
    assert not (tmp_path / f"{storage_key}.tmp").exists()


@pytest.mark.parametrize(
    "filename",
    [
        "../invoice.pdf",
        "nested/invoice.pdf",
        "/tmp/invoice.pdf",
        "..\\invoice.pdf",
    ],
)
def test_local_storage_rejects_path_traversal(
    tmp_path,
    filename: str,
) -> None:
    storage = LocalDocumentStorage(root=tmp_path)

    with pytest.raises(ValueError, match="must not contain a path"):
        storage.save(
            bundle_id=uuid4(),
            document_id=uuid4(),
            filename=filename,
            content=b"%PDF-1.7 test document",
        )


def test_local_storage_deletes_a_saved_file(tmp_path) -> None:
    storage = LocalDocumentStorage(root=tmp_path)
    document_id = uuid4()

    storage_key = storage.save(
        bundle_id=uuid4(),
        document_id=document_id,
        filename="invoice.pdf",
        content=b"%PDF-1.7 test document",
    )

    storage.delete(key=storage_key)

    assert not (tmp_path / storage_key).exists()


def test_local_storage_reads_a_saved_file(tmp_path) -> None:
    storage = LocalDocumentStorage(root=tmp_path)
    content = b"%PDF-1.7 test document"
    storage_key = storage.save(
        bundle_id=uuid4(),
        document_id=uuid4(),
        filename="invoice.pdf",
        content=content,
    )

    assert storage.read(key=storage_key) == content


def test_local_storage_refuses_to_delete_outside_storage_root(tmp_path) -> None:
    storage = LocalDocumentStorage(root=tmp_path)
    with pytest.raises(ValueError, match="outside the storage root"):
        storage.delete(key="../outside.pdf")
