from retrieval.types import ScoredChunk


def filter_by_role(chunks: list[ScoredChunk], user_role: str) -> list[ScoredChunk]:
    """Keep only chunks whose metadata allows the requested role."""
    allowed: list[ScoredChunk] = []
    role = user_role.strip().lower()
    for chunk in chunks:
        roles = chunk.metadata.get("allowed_roles") or ["support", "admin"]
        normalized = [str(item).strip().lower() for item in roles]
        if role in normalized:
            allowed.append(chunk)
    return allowed
