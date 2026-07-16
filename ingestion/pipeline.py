from dataclasses import dataclass
from pathlib import Path
import uuid

from api.config import Settings, settings as default_settings
from cache.invalidate import invalidate_cache
from db.session import run_migrations
from ingestion.chunker import chunk_text
from ingestion.embedder import embed_texts
from ingestion.store import save_chunks


@dataclass
class IngestResult:
    doc_id: str
    source: str
    chunk_count: int


def ingest_text(
    text: str,
    *,
    source: str,
    allowed_roles: list[str] | None = None,
    settings: Settings | None = None,
    embed_fn=embed_texts,
) -> IngestResult:
    cfg = settings or default_settings
    run_migrations(cfg.database_url)

    doc_id = str(uuid.uuid4())
    chunks = chunk_text(
        text,
        source=source,
        doc_id=doc_id,
        chunk_size=cfg.chunk_size,
        overlap=cfg.chunk_overlap,
        allowed_roles=allowed_roles,
    )
    if not chunks:
        return IngestResult(doc_id=doc_id, source=source, chunk_count=0)

    embeddings = embed_fn([c.text for c in chunks], settings=cfg)
    for chunk, embedding in zip(chunks, embeddings, strict=True):
        chunk.embedding = embedding

    count = save_chunks(chunks, database_url=cfg.database_url)
    invalidate_cache(settings=cfg)
    return IngestResult(doc_id=doc_id, source=source, chunk_count=count)


def ingest_file(
    path: str | Path,
    *,
    allowed_roles: list[str] | None = None,
    settings: Settings | None = None,
    embed_fn=embed_texts,
) -> IngestResult:
    file_path = Path(path)
    text = file_path.read_text(encoding="utf-8")
    return ingest_text(
        text,
        source=file_path.name,
        allowed_roles=allowed_roles,
        settings=settings,
        embed_fn=embed_fn,
    )
