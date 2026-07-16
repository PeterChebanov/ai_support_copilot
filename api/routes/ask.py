from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse

from api.config import Settings
from api.deps import get_settings
from api.models import AskRequest, AskResponse, Citation
from cache.middleware import cached_ask
from generation.generator import generate_answer
from retrieval.pipeline import retrieve
from security.guard import enforce_or_block

router = APIRouter(tags=["ask"])


def _run_ask(query: str, settings: Settings) -> AskResponse:
    retrieved = retrieve(query, settings=settings)
    generated = generate_answer(query, retrieved.chunks, settings=settings)
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


@router.post("/ask")
def ask_question(
    body: AskRequest,
    settings: Settings = Depends(get_settings),
) -> JSONResponse:
    blocked = enforce_or_block(body.query)
    if blocked is not None:
        return blocked

    response, meta = cached_ask(
        body.query,
        lambda query: _run_ask(query, settings),
        settings=settings,
    )
    headers = {
        "X-Cache": meta.cache,
        "X-Latency-Ms": f"{meta.latency_ms:.1f}",
        "X-Tokens-Saved": str(meta.tokens_saved),
    }
    if meta.cache_type:
        headers["X-Cache-Type"] = meta.cache_type
    return JSONResponse(content=response.model_dump(), headers=headers)
