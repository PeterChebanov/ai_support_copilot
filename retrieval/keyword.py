import json

import psycopg

from retrieval.types import ScoredChunk


def keyword_search(
    query: str,
    *,
    database_url: str,
    limit: int = 20,
) -> list[ScoredChunk]:
    """Full-text search over content_tsv (Postgres BM25-style ranking via ts_rank_cd)."""
    if not query.strip():
        return []

    with psycopg.connect(database_url) as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, doc_id, source, chunk_index, text, metadata,
                       ts_rank_cd(content_tsv, plainto_tsquery('english', %s)) AS rank
                FROM chunks
                WHERE content_tsv @@ plainto_tsquery('english', %s)
                ORDER BY rank DESC
                LIMIT %s
                """,
                (query, query, limit),
            )
            rows = cur.fetchall()

    return [
        ScoredChunk(
            id=str(row[0]),
            doc_id=str(row[1]),
            source=row[2],
            chunk_index=row[3],
            text=row[4],
            metadata=row[5] if isinstance(row[5], dict) else json.loads(row[5]),
            score=float(row[6]),
            keyword_score=float(row[6]),
        )
        for row in rows
    ]
