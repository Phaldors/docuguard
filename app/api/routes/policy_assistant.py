from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status

from app.policy_assistant.answer import PolicyAssistant
from app.policy_assistant.dependencies import (
    get_embedder,
    get_policy_assistant,
    get_policy_index,
    get_reranker,
)
from app.policy_assistant.embedder import Embedder
from app.policy_assistant.reranker import Reranker
from app.policy_assistant.retrieval import IndexedChunk
from app.schemas.policy_assistant import (
    AskPolicyQuestionRequest,
    AskPolicyQuestionResponse,
    CitationResponse,
)
from app.security.public_demo import block_public_demo_protected_endpoint
from app.services.policy_assistant import EmptyCorpusError, ask_policy_question

router = APIRouter(prefix="/policy-assistant", tags=["policy-assistant"])


@router.post("/ask", response_model=AskPolicyQuestionResponse)
async def ask_policy_question_route(
    payload: AskPolicyQuestionRequest,
    embedder: Annotated[Embedder | None, Depends(get_embedder)],
    reranker: Annotated[Reranker | None, Depends(get_reranker)],
    assistant: Annotated[PolicyAssistant | None, Depends(get_policy_assistant)],
    index: Annotated[list[IndexedChunk], Depends(get_policy_index)],
) -> AskPolicyQuestionResponse:
    block_public_demo_protected_endpoint()
    if embedder is None or reranker is None or assistant is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The policy assistant is not configured.",
        )

    try:
        answer = await ask_policy_question(
            query=payload.question,
            index=index,
            embedder=embedder,
            reranker=reranker,
            assistant=assistant,
        )
    except EmptyCorpusError:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="The policy index has not been built yet.",
        ) from None

    by_id = {indexed.chunk.chunk_id: indexed.chunk for indexed in index}
    citations = [
        CitationResponse(
            chunk_id=citation.chunk_id,
            document_path=by_id[citation.chunk_id].document_path,
            heading=by_id[citation.chunk_id].heading,
            quote=citation.quote,
        )
        for citation in answer.citations
        if citation.chunk_id in by_id
    ]

    return AskPolicyQuestionResponse(
        answer=answer.answer,
        grounded=answer.grounded,
        citations=citations,
    )
