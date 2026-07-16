import json

import psycopg
from pgvector.psycopg import register_vector

from retrieval.types import ScoredChunk


def vector_search(
    query_embedding: list[float],
    *,
    database_url: str,
    limit: int = 20,
) -> list[ScoredChunk]:
    """Nearest-neighbor search with pgvector cosine distance (<=>)."""
    if not query_embedding:
        return []

    with psycopg.connect(database_url) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT id, doc_id, source, chunk_index, text, metadata,
                       1 - (embedding <=> %s::vector) AS score
                FROM chunks
                WHERE embedding IS NOT NULL
                ORDER BY embedding <=> %s::vector
                LIMIT %s
                """,
                (query_embedding, query_embedding, limit),
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
            vector_score=float(row[6]),
        )
        for row in rows
    ]
