import json
from dataclasses import dataclass

from openai import OpenAI

from api.config import Settings, settings as default_settings
from generation.citations import RawCitation, validate_citations
from generation.prompt import build_messages
from retrieval.types import ScoredChunk


@dataclass
class GeneratedAnswer:
    query: str
    answer: str
    citations: list[RawCitation]


def _parse_llm_json(content: str) -> tuple[str, list[RawCitation]]:
    payload = json.loads(content)
    answer = str(payload.get("answer", "")).strip()
    raw_citations = payload.get("citations") or []
    citations: list[RawCitation] = []
    for item in raw_citations:
        if not isinstance(item, dict):
            continue
        chunk_id = str(item.get("chunk_id", "")).strip()
        quote = str(item.get("quote", "")).strip()
        source = str(item.get("source", "")).strip()
        if chunk_id and quote:
            citations.append(RawCitation(chunk_id=chunk_id, source=source, quote=quote))
    return answer, citations


def generate_answer(
    query: str,
    chunks: list[ScoredChunk],
    *,
    settings: Settings | None = None,
    client: OpenAI | None = None,
) -> GeneratedAnswer:
    cfg = settings or default_settings
    if not cfg.openai_api_key:
        raise ValueError("OPENAI_API_KEY is required for generation")

    openai_client = client or OpenAI(api_key=cfg.openai_api_key)
    messages = build_messages(query, chunks)
    response = openai_client.chat.completions.create(
        model=cfg.llm_model,
        messages=messages,
        response_format={"type": "json_object"},
        temperature=0,
    )
    content = response.choices[0].message.content or "{}"
    answer, raw_citations = _parse_llm_json(content)
    valid_citations = validate_citations(answer, raw_citations, chunks)
    return GeneratedAnswer(query=query, answer=answer, citations=valid_citations)
