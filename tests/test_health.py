from fastapi.testclient import TestClient

from api.main import app


def test_health_returns_ok():
    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_ready_returns_dependency_status(monkeypatch):
    class FakeCursor:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def execute(self, _sql):
            return None

    class FakeConn:
        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def cursor(self):
            return FakeCursor()

    class FakeRedis:
        def ping(self):
            return True

    monkeypatch.setattr("api.routes.health.psycopg.connect", lambda _url: FakeConn())
    monkeypatch.setattr("api.routes.health.redis.from_url", lambda _url: FakeRedis())

    client = TestClient(app)
    response = client.get("/ready")
    assert response.status_code == 200
    assert response.json() == {"status": "ready", "postgres": "ok", "redis": "ok"}
