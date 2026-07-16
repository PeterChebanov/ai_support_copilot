from dataclasses import dataclass

from generation.prompt import NO_INFO_ANSWER
from retrieval.types import ScoredChunk


@dataclass
class RawCitation:
    chunk_id: str
    source: str
    quote: str


def _normalize_for_match(text: str) -> str:
    return " ".join(text.lower().split())


def _quote_in_chunk(quote: str, chunk_text: str) -> bool:
    return _normalize_for_match(quote) in _normalize_for_match(chunk_text)


def _valid_quote_spans(quote: str, chunk_text: str) -> list[str]:
    cleaned = quote.strip()
    if not cleaned:
        return []
    if _quote_in_chunk(cleaned, chunk_text):
        return [cleaned]

    import re

    sentences = re.split(r"(?<=[.!?])\s+", cleaned)
    return [sentence for sentence in sentences if sentence.strip() and _quote_in_chunk(sentence, chunk_text)]


def is_no_info_answer(answer: str) -> bool:
    normalized = answer.strip().lower()
    return normalized == NO_INFO_ANSWER.lower() or "no relevant information" in normalized


def validate_citations(
    answer: str,
    citations: list[RawCitation],
    chunks: list[ScoredChunk],
) -> list[RawCitation]:
    if not citations:
        if is_no_info_answer(answer):
            return []
        return []

    chunk_by_id = {chunk.id: chunk for chunk in chunks}
    valid: list[RawCitation] = []
    for citation in citations:
        chunk = chunk_by_id.get(citation.chunk_id)
        if chunk is None:
            continue
        if not _quote_in_chunk(citation.quote, chunk.text):
            spans = _valid_quote_spans(citation.quote, chunk.text)
            if not spans:
                continue
            for span in spans:
                valid.append(
                    RawCitation(
                        chunk_id=citation.chunk_id,
                        source=chunk.source,
                        quote=span,
                    )
                )
            continue
        valid.append(
            RawCitation(
                chunk_id=citation.chunk_id,
                source=chunk.source,
                quote=citation.quote,
            )
        )
    return valid
