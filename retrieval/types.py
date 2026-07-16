from dataclasses import dataclass, field
from typing import Any


@dataclass
class ScoredChunk:
    id: str
    doc_id: str
    source: str
    chunk_index: int
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)
    score: float = 0.0
    vector_score: float | None = None
    keyword_score: float | None = None
    rrf_score: float | None = None
