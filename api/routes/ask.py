from fastapi import APIRouter, Depends

from api.config import Settings
from api.deps import get_settings
from api.models import AskRequest, AskResponse, Citation
from generation.generator import generate_answer
from retrieval.pipeline import retrieve

router = APIRouter(tags=["ask"])


@router.post("/ask", response_model=AskResponse)
def ask_question(
    body: AskRequest,
    settings: Settings = Depends(get_settings),
) -> AskResponse:
    retrieved = retrieve(body.query, settings=settings)
    generated = generate_answer(body.query, retrieved.chunks, settings=settings)
    return AskResponse(
        query=generated.query,
        answer=generated.answer,
        citations=[
            Citation(
                chunk_id=c.chunk_id,
                source=c.source,
                quote=c.quote,
            )
            for c in generated.citations
        ],
    )
