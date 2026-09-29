"""The policy assistant's grounding corpus.

Per docs/product-brief.md, the policy assistant is isolated from the
decision pipeline: it answers questions about how DocuGuard itself works
(routing policy, discrepancy taxonomy, decision ownership), not about the
content of a specific document bundle. Its corpus is therefore DocuGuard's
own design documents, not a licensed external dataset -- there is no
licensing question, and no tenant/customer data ever enters it.

Access-aware tooling starts here: retrieval is restricted to this fixed,
explicit allow-list of paths. There is no filesystem globbing from a
request, so a query can never pull in a document outside this set.
"""

from dataclasses import dataclass
from pathlib import Path

POLICY_DOCUMENTS: tuple[Path, ...] = (
    Path("docs/product-brief.md"),
    Path("docs/data-contract.md"),
    Path("docs/reviewer-workflow.md"),
)


@dataclass(frozen=True)
class PolicyChunk:
    chunk_id: str
    document_path: str
    heading: str
    text: str


def load_policy_chunks(
    *, documents: tuple[Path, ...] = POLICY_DOCUMENTS
) -> list[PolicyChunk]:
    chunks: list[PolicyChunk] = []
    for path in documents:
        chunks.extend(_split_into_sections(path, path.read_text()))
    return chunks


def _split_into_sections(path: Path, content: str) -> list[PolicyChunk]:
    sections: list[tuple[str, list[str]]] = []
    heading = path.stem
    body: list[str] = []

    for line in content.splitlines():
        if line.startswith("## "):
            if body:
                sections.append((heading, body))
            heading = line.removeprefix("## ").strip()
            body = []
        else:
            body.append(line)
    if body:
        sections.append((heading, body))

    chunks: list[PolicyChunk] = []
    for index, (section_heading, section_lines) in enumerate(sections):
        text = "\n".join(section_lines).strip()
        if not text:
            continue
        chunks.append(
            PolicyChunk(
                chunk_id=f"{path.name}#{index}",
                document_path=str(path),
                heading=section_heading,
                text=text,
            )
        )
    return chunks
