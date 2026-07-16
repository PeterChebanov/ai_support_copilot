from dataclasses import dataclass, field
from typing import Any


@dataclass
class TextChunk:
    text: str
    chunk_index: int
    source: str
    doc_id: str
    metadata: dict[str, Any] = field(default_factory=dict)
    embedding: list[float] | None = None
    id: str | None = None


def chunk_text(
    text: str,
    *,
    source: str,
    doc_id: str,
    chunk_size: int = 512,
    overlap: int = 64,
    allowed_roles: list[str] | None = None,
) -> list[TextChunk]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap >= chunk_size:
        raise ValueError("overlap must be smaller than chunk_size")

    normalized = text.replace("\r\n", "\n").strip()
    if not normalized:
        return []

    roles = allowed_roles or ["support", "admin"]
    chunks: list[TextChunk] = []
    start = 0
    index = 0
    step = chunk_size - overlap

    while start < len(normalized):
        end = min(start + chunk_size, len(normalized))
        piece = normalized[start:end].strip()
        if piece:
            chunks.append(
                TextChunk(
                    text=piece,
                    chunk_index=index,
                    source=source,
                    doc_id=doc_id,
                    metadata={
                        "source": source,
                        "doc_id": doc_id,
                        "chunk_index": index,
                        "allowed_roles": roles,
                    },
                )
            )
            index += 1
        if end >= len(normalized):
            break
        start += step

    return chunks
