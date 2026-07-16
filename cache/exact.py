import hashlib

import redis

from api.config import Settings, settings as default_settings
from api.models import AskResponse


def _exact_key(query: str) -> str:
    digest = hashlib.sha256(query.strip().lower().encode("utf-8")).hexdigest()
    return f"cache:exact:{digest}"


def get_exact(
    query: str,
    *,
    settings: Settings | None = None,
    redis_client: redis.Redis | None = None,
) -> AskResponse | None:
    cfg = settings or default_settings
    client = redis_client or redis.from_url(cfg.redis_url, decode_responses=True)
    raw = client.get(_exact_key(query))
    if not raw:
        return None
    return AskResponse.model_validate_json(raw)


def set_exact(
    query: str,
    response: AskResponse,
    *,
    settings: Settings | None = None,
    redis_client: redis.Redis | None = None,
) -> None:
    cfg = settings or default_settings
    client = redis_client or redis.from_url(cfg.redis_url, decode_responses=True)
    client.set(
        _exact_key(query),
        response.model_dump_json(),
        ex=cfg.cache_ttl_seconds,
    )
