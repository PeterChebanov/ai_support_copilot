from dataclasses import dataclass

from api.config import Settings, settings as default_settings
from db.session import run_migrations
from ingestion.embedder import embed_texts
from retrieval.acl import filter_by_role
from retrieval.fusion import reciprocal_rank_fusion
from retrieval.keyword import keyword_search
from retrieval.rerank import rerank_chunks
from retrieval.types import ScoredChunk
from retrieval.vector import vector_search


@dataclass
class RetrieveResult:
    query: str
    chunks: list[ScoredChunk]


def retrieve(
    query: str,
    *,
    top_k: int | None = None,
    user_role: str = "support",
    settings: Settings | None = None,
    embed_fn=embed_texts,
) -> RetrieveResult:
    cfg = settings or default_settings
    run_migrations(cfg.database_url)

    limit = top_k or cfg.retrieve_top_k
    candidate_limit = cfg.retrieve_candidate_limit

    keyword_hits = keyword_search(
        query,
        database_url=cfg.database_url,
        limit=candidate_limit,
    )

    embeddings = embed_fn([query], settings=cfg)
    query_embedding = embeddings[0] if embeddings else []
    vector_hits = vector_search(
        query_embedding,
        database_url=cfg.database_url,
        limit=candidate_limit,
    )

    fused = reciprocal_rank_fusion(
        keyword_hits,
        vector_hits,
        k=cfg.rrf_k,
    )
    scoped = filter_by_role(fused, user_role)
    ranked = rerank_chunks(scoped)
    return RetrieveResult(query=query, chunks=ranked[:limit])
