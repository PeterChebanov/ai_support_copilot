from retrieval.types import ScoredChunk


def reciprocal_rank_fusion(
    *ranked_lists: list[ScoredChunk],
    k: int = 60,
) -> list[ScoredChunk]:
    """Merge ranked lists with Reciprocal Rank Fusion: 1 / (k + rank)."""
    by_id: dict[str, ScoredChunk] = {}
    scores: dict[str, float] = {}

    for ranked in ranked_lists:
        for rank, chunk in enumerate(ranked, start=1):
            scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
            if chunk.id not in by_id:
                by_id[chunk.id] = ScoredChunk(
                    id=chunk.id,
                    doc_id=chunk.doc_id,
                    source=chunk.source,
                    chunk_index=chunk.chunk_index,
                    text=chunk.text,
                    metadata=dict(chunk.metadata),
                    vector_score=chunk.vector_score,
                    keyword_score=chunk.keyword_score,
                )
            else:
                existing = by_id[chunk.id]
                if chunk.vector_score is not None:
                    existing.vector_score = chunk.vector_score
                if chunk.keyword_score is not None:
                    existing.keyword_score = chunk.keyword_score

    fused: list[ScoredChunk] = []
    for chunk_id, rrf in scores.items():
        chunk = by_id[chunk_id]
        chunk.rrf_score = rrf
        chunk.score = rrf
        fused.append(chunk)

    fused.sort(key=lambda c: c.score, reverse=True)
    return fused
