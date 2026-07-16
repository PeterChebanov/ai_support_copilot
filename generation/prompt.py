from retrieval.types import ScoredChunk

SYSTEM_PROMPT = """You are a support knowledge assistant. Answer ONLY using the provided context chunks.

Rules:
- If the context does not contain enough information, respond with answer exactly:
  "I do not have relevant information in the knowledge base to answer this question."
  and return an empty citations array.
- Every factual claim must be supported by at least one citation.
- Each citation quote MUST be one **contiguous** span copied verbatim from the chunk — never skip sentences in the middle.
- Prefer one or two short sentences per citation — copy them verbatim, including markdown markers like **bold**.
- Use one citation per distinct span; do not merge non-adjacent sentences into a single quote.
- Do not invent policies, numbers, or steps not present in the context.
- Be concise and professional."""

NO_INFO_ANSWER = (
    "I do not have relevant information in the knowledge base to answer this question."
)


def format_context_chunks(chunks: list[ScoredChunk]) -> str:
    if not chunks:
        return "(no context retrieved)"
    parts: list[str] = []
    for chunk in chunks:
        parts.append(
            f"[chunk_id={chunk.id} source={chunk.source} chunk_index={chunk.chunk_index}]\n"
            f"{chunk.text}"
        )
    return "\n\n---\n\n".join(parts)


def build_messages(query: str, chunks: list[ScoredChunk]) -> list[dict[str, str]]:
    context = format_context_chunks(chunks)
    user_content = (
        f"Context chunks:\n\n{context}\n\n"
        f"User question: {query}\n\n"
        "Respond with JSON matching this schema:\n"
        '{"answer": "string", "citations": [{"chunk_id": "uuid", "source": "filename", "quote": "exact substring"}]}'
    )
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_content},
    ]
