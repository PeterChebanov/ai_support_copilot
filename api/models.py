from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    doc_id: str
    source: str
    chunk_count: int = Field(description="Number of chunks stored for this document")
