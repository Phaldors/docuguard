from typing import Literal

from openai import AsyncOpenAI
from pydantic import BaseModel, ConfigDict, Field


class ExtractedField(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str | None
    evidence: str | None
    confidence: float = Field(ge=0, le=1)


class DocumentFields(BaseModel):
    model_config = ConfigDict(extra="forbid")

    document_type: Literal["invoice", "purchase_order", "delivery_note", "other"]
    supplier_name: ExtractedField
    document_number: ExtractedField
    document_date: ExtractedField
    currency: ExtractedField
    total: ExtractedField


EXTRACTION_INSTRUCTIONS = """Extract document fields from the supplied text.
Use only evidence present in the text. Do not infer missing values.
For each field, return the exact supporting text as evidence. If a field is
missing, return null for value and evidence with confidence 0.0.
Return dates and totals exactly as written; do not normalize them.

supplier_name is the name of the business or store that issued this
document, normally found in a header/letterhead area (often the first line
of a receipt or invoice). It is never a purchased product, menu item, line
item description, or payment method. If the only candidate text is a
product or line item name, treat supplier_name as missing rather than
returning that text."""


class StructuredDocumentExtractor:
    def __init__(self, *, api_key: str, model: str) -> None:
        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def extract(self, *, document_text: str) -> DocumentFields:
        response = await self.client.responses.create(
            model=self.model,
            input=[
                {"role": "system", "content": EXTRACTION_INSTRUCTIONS},
                {"role": "user", "content": document_text},
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "document_fields",
                    "strict": True,
                    "schema": DocumentFields.model_json_schema(),
                }
            },
        )

        if not response.output_text:
            raise ValueError("The model returned no extraction output.")

        return DocumentFields.model_validate_json(response.output_text)
