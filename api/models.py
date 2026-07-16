from pydantic import BaseModel, Field


class IngestResponse(BaseModel):
    doc_id: str
    source: str
    chunk_count: int = Field(description="Number of chunks stored for this document")


class RetrieveRequest(BaseModel):
    query: str = Field(min_length=1, description="Support question to search for")
    top_k: int | None = Field(default=None, ge=1, le=50)
    user_role: str = Field(default="support", min_length=1)


class RetrievedChunk(BaseModel):
    id: str
    doc_id: str
    source: str
    chunk_index: int
    text: str
    score: float
    metadata: dict = Field(default_factory=dict)


class RetrieveResponse(BaseModel):
    query: str
    chunks: list[RetrievedChunk]


class AskRequest(BaseModel):
    query: str = Field(min_length=1, description="Support question to answer")
    user_role: str = Field(default="support", min_length=1)


class Citation(BaseModel):
    chunk_id: str
    source: str
    quote: str = Field(description="Exact substring from the cited chunk text")


class AskResponse(BaseModel):
    query: str
    answer: str
    citations: list[Citation] = Field(default_factory=list)
