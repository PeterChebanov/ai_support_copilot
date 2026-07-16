import json
import math
import uuid

import redis

from api.config import Settings, settings as default_settings
from api.models import AskResponse

SEMANTIC_INDEX_KEY = "cache:semantic:index"


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b, strict=True))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def get_semantic(
    embedding: list[float],
    *,
    settings: Settings | None = None,
    redis_client: redis.Redis | None = None,
) -> AskResponse | None:
    cfg = settings or default_settings
    client = redis_client or redis.from_url(cfg.redis_url, decode_responses=True)
    best_score = 0.0
    best_response: AskResponse | None = None

    for key in client.lrange(SEMANTIC_INDEX_KEY, 0, -1):
        raw = client.get(key)
        if not raw:
            client.lrem(SEMANTIC_INDEX_KEY, 0, key)
            continue
        payload = json.loads(raw)
        score = _cosine_similarity(embedding, payload["embedding"])
        if score > best_score:
            best_score = score
            best_response = AskResponse.model_validate(payload["response"])

    if best_score >= cfg.semantic_cache_threshold and best_response is not None:
        return best_response
    return None


def set_semantic(
    embedding: list[float],
    response: AskResponse,
    *,
    settings: Settings | None = None,
    redis_client: redis.Redis | None = None,
) -> None:
    cfg = settings or default_settings
    client = redis_client or redis.from_url(cfg.redis_url, decode_responses=True)
    key = f"cache:semantic:{uuid.uuid4().hex}"
    payload = json.dumps({"embedding": embedding, "response": response.model_dump()})
    client.set(key, payload, ex=cfg.cache_ttl_seconds)
    client.rpush(SEMANTIC_INDEX_KEY, key)

    while client.llen(SEMANTIC_INDEX_KEY) > cfg.semantic_cache_max_entries:
        oldest = client.lpop(SEMANTIC_INDEX_KEY)
        if oldest:
            client.delete(oldest)
