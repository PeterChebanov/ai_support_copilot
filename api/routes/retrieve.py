from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.config import Settings
from api.deps import get_settings
from api.models import RetrieveRequest, RetrieveResponse, RetrievedChunk
from retrieval.pipeline import retrieve
from security.guard import enforce_or_block

router = APIRouter(tags=["retrieve"])


@router.post("/retrieve", response_model=None)
def retrieve_chunks(
    body: RetrieveRequest,
    settings: Settings = Depends(get_settings),
) -> RetrieveResponse | JSONResponse:
    blocked = enforce_or_block(body.query)
    if blocked is not None:
        return blocked

    result = retrieve(body.query, top_k=body.top_k, user_role=body.user_role, settings=settings)
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
