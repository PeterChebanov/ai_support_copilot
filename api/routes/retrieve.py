from fastapi import APIRouter, Depends

from api.config import Settings
from api.deps import get_settings
from api.models import RetrieveRequest, RetrieveResponse, RetrievedChunk
from retrieval.pipeline import retrieve

router = APIRouter(tags=["retrieve"])


@router.post("/retrieve", response_model=RetrieveResponse)
def retrieve_chunks(
    body: RetrieveRequest,
    settings: Settings = Depends(get_settings),
) -> RetrieveResponse:
    result = retrieve(body.query, top_k=body.top_k, settings=settings)
    return RetrieveResponse(
        query=result.query,
        chunks=[
            RetrievedChunk(
                id=c.id,
                doc_id=c.doc_id,
                source=c.source,
                chunk_index=c.chunk_index,
                text=c.text,
                score=c.score,
                metadata=c.metadata,
            )
            for c in result.chunks
        ],
    )
