import pytest

from api.models import AskResponse, Citation
from cache.exact import get_exact, set_exact
from cache.invalidate import invalidate_cache
from cache.middleware import cached_ask
from cache.semantic import get_semantic, set_semantic


class FakeRedis:
    def __init__(self) -> None:
        self.store: dict[str, str] = {}
        self.lists: dict[str, list[str]] = {}
        self.ttl: dict[str, int | None] = {}

    def get(self, key: str) -> str | None:
        return self.store.get(key)

    def set(self, key: str, value: str, ex: int | None = None) -> None:
        self.store[key] = value
        self.ttl[key] = ex

    def delete(self, key: str) -> None:
        self.store.pop(key, None)
        self.ttl.pop(key, None)
        self.lists.pop(key, None)

    def rpush(self, key: str, value: str) -> None:
        self.lists.setdefault(key, []).append(value)

    def lrange(self, key: str, start: int, end: int) -> list[str]:
        items = self.lists.get(key, [])
        return items[start : end + 1 if end >= 0 else None]

    def lrem(self, key: str, count: int, value: str) -> None:
        items = self.lists.get(key, [])
        while count != 0 and value in items:
            items.remove(value)
            count -= 1

    def llen(self, key: str) -> int:
        return len(self.lists.get(key, []))

    def lpop(self, key: str) -> str | None:
        items = self.lists.get(key, [])
        return items.pop(0) if items else None

    def scan_iter(self, match: str = "*"):
        prefix = match.rstrip("*")
        for key in list(self.store):
            if key.startswith(prefix):
                yield key
        for key in list(self.lists):
            if key.startswith(prefix):
                yield key


@pytest.fixture
def fake_redis() -> FakeRedis:
    return FakeRedis()


def _sample_response(query: str = "refund policy") -> AskResponse:
    return AskResponse(
        query=query,
        answer="Refunds within 30 days.",
        citations=[
            Citation(
                chunk_id="c1",
                source="policies.md",
                quote="full refund within **30 days**",
            )
        ],
    )


def test_exact_cache_hit(fake_redis: FakeRedis):
    from api.config import Settings

    cfg = Settings(openai_api_key="test", redis_url="redis://localhost:6379/0")
    response = _sample_response()
    set_exact("refund policy", response, user_role="support", settings=cfg, redis_client=fake_redis)  # type: ignore[arg-type]

    hit = get_exact("refund policy", user_role="support", settings=cfg, redis_client=fake_redis)  # type: ignore[arg-type]
    assert hit is not None
    assert hit.answer == response.answer


def test_semantic_cache_hit_on_similar_embedding(fake_redis: FakeRedis):
    from api.config import Settings

    cfg = Settings(
        openai_api_key="test",
        redis_url="redis://localhost:6379/0",
        semantic_cache_threshold=0.99,
    )
    response = _sample_response("What is your refund policy?")
    base = [1.0, 0.0, 0.0]
    near = [0.999, 0.001, 0.0]
    set_semantic(base, response, user_role="support", settings=cfg, redis_client=fake_redis)  # type: ignore[arg-type]

    hit = get_semantic(near, user_role="support", settings=cfg, redis_client=fake_redis)  # type: ignore[arg-type]
    assert hit is not None
    assert hit.answer == response.answer


def test_cached_ask_exact_then_semantic():
    from api.config import Settings

    cfg = Settings(openai_api_key="test", redis_url="redis://localhost:6379/0")
    fake = FakeRedis()
    calls = {"count": 0}

    def ask_fn(query: str) -> AskResponse:
        calls["count"] += 1
        return _sample_response(query)

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("cache.exact.redis.from_url", lambda *a, **k: fake)
        mp.setattr("cache.semantic.redis.from_url", lambda *a, **k: fake)
        mp.setattr(
            "cache.middleware.get_exact",
            lambda q, user_role="support", **k: get_exact(
                q, user_role=user_role, settings=cfg, redis_client=fake
            ),
        )
        mp.setattr(
            "cache.middleware.set_exact",
            lambda q, r, user_role="support", **k: set_exact(
                q, r, user_role=user_role, settings=cfg, redis_client=fake
            ),
        )
        mp.setattr(
            "cache.middleware.get_semantic",
            lambda emb, user_role="support", **k: get_semantic(
                emb, user_role=user_role, settings=cfg, redis_client=fake
            ),
        )
        mp.setattr(
            "cache.middleware.set_semantic",
            lambda emb, r, user_role="support", **k: set_semantic(
                emb, r, user_role=user_role, settings=cfg, redis_client=fake
            ),
        )

        def embed(texts, settings=None):
            return [[1.0, 0.0, 0.0]]

        miss, meta_miss = cached_ask(
            "refund policy", ask_fn, user_role="support", settings=cfg, embed_fn=embed
        )
        hit, meta_hit = cached_ask(
            "refund policy", ask_fn, user_role="support", settings=cfg, embed_fn=embed
        )

    assert calls["count"] == 1
    assert meta_miss.cache == "MISS"
    assert meta_hit.cache == "HIT"
    assert meta_hit.cache_type == "exact"
    assert hit.answer == miss.answer


def test_invalidate_cache_clears_keys(fake_redis: FakeRedis):
    from api.config import Settings

    cfg = Settings(openai_api_key="test", redis_url="redis://localhost:6379/0")
    set_exact("q", _sample_response(), user_role="support", settings=cfg, redis_client=fake_redis)  # type: ignore[arg-type]
    fake_redis.store["cache:semantic:dummy"] = "x"

    deleted = invalidate_cache(settings=cfg, redis_client=fake_redis)  # type: ignore[arg-type]
    assert deleted >= 1
    assert get_exact("q", user_role="support", settings=cfg, redis_client=fake_redis) is None  # type: ignore[arg-type]


def test_ask_endpoint_returns_cache_headers():
    from fastapi.testclient import TestClient

    from api.main import app
    from cache.middleware import CacheMeta

    sample = _sample_response("What is the refund policy?")

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "api.routes.ask.cached_ask",
            lambda q, fn, **k: (
                sample,
                CacheMeta(cache="HIT", cache_type="semantic", latency_ms=12.5, tokens_saved=800),
            ),
        )
        client = TestClient(app)
        response = client.post("/ask", json={"query": "What is your refund policy?"})

    assert response.status_code == 200
    assert response.headers["X-Cache"] == "HIT"
    assert response.headers["X-Cache-Type"] == "semantic"
    assert response.headers["X-Tokens-Saved"] == "800"


def test_cache_is_scoped_by_user_role(fake_redis: FakeRedis):
    from api.config import Settings

    cfg = Settings(openai_api_key="test", redis_url="redis://localhost:6379/0")
    response = _sample_response("admin salary policy")

    set_exact(
        "admin salary policy",
        response,
        user_role="admin",
        settings=cfg,
        redis_client=fake_redis,
    )  # type: ignore[arg-type]

    admin_hit = get_exact(
        "admin salary policy",
        user_role="admin",
        settings=cfg,
        redis_client=fake_redis,
    )  # type: ignore[arg-type]
    support_hit = get_exact(
        "admin salary policy",
        user_role="support",
        settings=cfg,
        redis_client=fake_redis,
    )  # type: ignore[arg-type]

    assert admin_hit is not None
    assert support_hit is None
