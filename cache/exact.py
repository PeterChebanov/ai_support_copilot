import hashlib

import redis

from api.config import Settings, settings as default_settings
from api.models import AskResponse


def _exact_key(query: str, user_role: str = "support") -> str:
    payload = f"{user_role.strip().lower()}::{query.strip().lower()}"
    digest = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    return f"cache:exact:{digest}"


def get_exact(
    query: str,
    *,
    user_role: str = "support",
    settings: Settings | None = None,
    redis_client: redis.Redis | None = None,
) -> AskResponse | None:
    cfg = settings or default_settings
    client = redis_client or redis.from_url(cfg.redis_url, decode_responses=True)
    raw = client.get(_exact_key(query, user_role))
    if not raw:
        return None
    return AskResponse.model_validate_json(raw)


def set_exact(
    query: str,
    response: AskResponse,
    *,
    user_role: str = "support",
    settings: Settings | None = None,
    redis_client: redis.Redis | None = None,
) -> None:
    cfg = settings or default_settings
    client = redis_client or redis.from_url(cfg.redis_url, decode_responses=True)
    client.set(
        _exact_key(query, user_role),
        response.model_dump_json(),
        ex=cfg.cache_ttl_seconds,
    )
