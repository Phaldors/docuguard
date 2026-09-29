from app.policy_assistant.corpus import POLICY_DOCUMENTS, load_policy_chunks


def test_every_configured_policy_document_produces_at_least_one_chunk() -> None:
    chunks = load_policy_chunks()

    document_paths_with_chunks = {chunk.document_path for chunk in chunks}
    for path in POLICY_DOCUMENTS:
        assert str(path) in document_paths_with_chunks


def test_chunk_ids_are_unique_and_non_empty() -> None:
    chunks = load_policy_chunks()

    chunk_ids = [chunk.chunk_id for chunk in chunks]
    assert len(chunk_ids) == len(set(chunk_ids))
    assert all(chunk.text.strip() for chunk in chunks)


def test_a_known_section_heading_is_captured() -> None:
    chunks = load_policy_chunks()

    headings = {chunk.heading for chunk in chunks}
    assert "Routing policy" in headings
