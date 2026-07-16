import json
import uuid

import psycopg
from pgvector.psycopg import register_vector

from ingestion.chunker import TextChunk


def save_chunks(chunks: list[TextChunk], *, database_url: str) -> int:
    if not chunks:
        return 0

    doc_id = chunks[0].doc_id
    with psycopg.connect(database_url) as conn:
        register_vector(conn)
        with conn.cursor() as cur:
            cur.execute("DELETE FROM chunks WHERE doc_id = %s", (doc_id,))
            for chunk in chunks:
                chunk_id = chunk.id or str(uuid.uuid4())
                if chunk.embedding is None:
                    raise ValueError("chunk.embedding is required before save")
                cur.execute(
                    """
                    INSERT INTO chunks (id, doc_id, source, chunk_index, text, metadata, embedding)
                    VALUES (%s, %s, %s, %s, %s, %s, %s)
                    """,
                    (
                        chunk_id,
                        chunk.doc_id,
                        chunk.source,
                        chunk.chunk_index,
                        chunk.text,
                        json.dumps(chunk.metadata),
                        chunk.embedding,
                    ),
                )
        conn.commit()
    return len(chunks)
