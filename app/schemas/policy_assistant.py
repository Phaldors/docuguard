from pydantic import BaseModel, ConfigDict, Field


class AskPolicyQuestionRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    question: str = Field(min_length=1, max_length=2000)


class CitationResponse(BaseModel):
    chunk_id: str
    document_path: str
    heading: str
    quote: str


class AskPolicyQuestionResponse(BaseModel):
    answer: str
    grounded: bool
    citations: list[CitationResponse]
