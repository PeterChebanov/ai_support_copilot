import redis

from api.config import Settings, settings as default_settings

CACHE_KEY_PREFIX = "cache:"


def invalidate_cache(
    *,
    settings: Settings | None = None,
    redis_client: redis.Redis | None = None,
) -> int:
    """Clear cached ask responses after knowledge-base changes."""
    cfg = settings or default_settings
    client = redis_client or redis.from_url(cfg.redis_url, decode_responses=True)
    deleted = 0
    for key in client.scan_iter(f"{CACHE_KEY_PREFIX}*"):
        client.delete(key)
        deleted += 1
    return deleted
