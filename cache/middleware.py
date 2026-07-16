import time
from dataclasses import dataclass
from typing import Callable

from api.config import Settings, settings as default_settings
from api.models import AskResponse
from cache.exact import get_exact, set_exact
from cache.semantic import get_semantic, set_semantic
from ingestion.embedder import embed_texts


@dataclass
class CacheMeta:
    cache: str  # HIT | MISS
    cache_type: str | None = None  # exact | semantic
    latency_ms: float = 0.0
    tokens_saved: int = 0


def _with_query(response: AskResponse, query: str) -> AskResponse:
    return response.model_copy(update={"query": query})


def cached_ask(
    query: str,
    ask_fn: Callable[[str], AskResponse],
    *,
    user_role: str = "support",
    settings: Settings | None = None,
    embed_fn=embed_texts,
    estimated_tokens_per_ask: int = 800,
) -> tuple[AskResponse, CacheMeta]:
    cfg = settings or default_settings
    started = time.perf_counter()

    exact_hit = get_exact(query, user_role=user_role, settings=cfg)
    if exact_hit is not None:
        elapsed = (time.perf_counter() - started) * 1000
        return _with_query(exact_hit, query), CacheMeta(
            cache="HIT",
            cache_type="exact",
            latency_ms=elapsed,
            tokens_saved=estimated_tokens_per_ask,
        )

    embeddings = embed_fn([query], settings=cfg)
    query_embedding = embeddings[0] if embeddings else []
    if query_embedding:
        semantic_hit = get_semantic(query_embedding, user_role=user_role, settings=cfg)
        if semantic_hit is not None:
            elapsed = (time.perf_counter() - started) * 1000
            response = _with_query(semantic_hit, query)
            set_exact(query, response, user_role=user_role, settings=cfg)
            return response, CacheMeta(
                cache="HIT",
                cache_type="semantic",
                latency_ms=elapsed,
                tokens_saved=estimated_tokens_per_ask,
            )

    response = ask_fn(query)
    set_exact(query, response, user_role=user_role, settings=cfg)
    if query_embedding:
        set_semantic(query_embedding, response, user_role=user_role, settings=cfg)

    elapsed = (time.perf_counter() - started) * 1000
    return response, CacheMeta(cache="MISS", latency_ms=elapsed, tokens_saved=0)
