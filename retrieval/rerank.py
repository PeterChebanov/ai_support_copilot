from retrieval.types import ScoredChunk


def rerank_chunks(
    chunks: list[ScoredChunk],
    *,
    vector_weight: float = 0.7,
    keyword_weight: float = 0.3,
) -> list[ScoredChunk]:
    """
    Lightweight second-pass rerank over fused candidates.

    Combines normalized dense (vector) and sparse (keyword) signals so
    exact keyword hits and semantic neighbours both influence final order.
    """
    if not chunks:
        return []

    vector_vals = [c.vector_score or 0.0 for c in chunks]
    keyword_vals = [c.keyword_score or 0.0 for c in chunks]
    vmax = max(vector_vals) if vector_vals else 0.0
    kmax = max(keyword_vals) if keyword_vals else 0.0

    reranked: list[ScoredChunk] = []
    for chunk in chunks:
        v = (chunk.vector_score or 0.0) / vmax if vmax > 0 else 0.0
        kw = (chunk.keyword_score or 0.0) / kmax if kmax > 0 else 0.0
        # Preserve RRF as a small tie-breaker so unique fused hits stay ranked.
        rrf = chunk.rrf_score or 0.0
        chunk.score = vector_weight * v + keyword_weight * kw + 0.01 * rrf
        reranked.append(chunk)

    reranked.sort(key=lambda c: c.score, reverse=True)
    return reranked
