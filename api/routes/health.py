from fastapi import APIRouter, Depends
import psycopg
import redis

from api.config import Settings
from api.deps import get_settings

router = APIRouter(tags=["health"])


@router.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/ready")
def ready(settings: Settings = Depends(get_settings)) -> dict[str, str]:
    postgres_status = "ok"
    redis_status = "ok"

    try:
        with psycopg.connect(settings.database_url) as conn:
            with conn.cursor() as cur:
                cur.execute("SELECT 1")
    except Exception:
        postgres_status = "error"

    try:
        client = redis.from_url(settings.redis_url)
        client.ping()
    except Exception:
        redis_status = "error"

    overall = "ready" if postgres_status == "ok" and redis_status == "ok" else "degraded"
    return {"status": overall, "postgres": postgres_status, "redis": redis_status}
