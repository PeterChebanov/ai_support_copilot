from unittest.mock import MagicMock


def test_ask_endpoint_support_role_cannot_see_admin_chunks():
    from fastapi.testclient import TestClient

    import pytest

    from api.main import app
    from cache.middleware import CacheMeta
    from generation.prompt import NO_INFO_ANSWER

    mock_generated = MagicMock()
    mock_generated.query = "admin salary policy"
    mock_generated.answer = NO_INFO_ANSWER
    mock_generated.citations = []

    with pytest.MonkeyPatch.context() as mp:
        def fake_retrieve(query, *, user_role="support", **kwargs):
            result = MagicMock()
            result.query = query
            result.chunks = [] if user_role == "support" else [
                MagicMock(
                    id="admin1",
                    doc_id="doc-admin",
                    source="internal-admin.md",
                    chunk_index=0,
                    text="Junior support agents: **€38,000-€46,000** annual gross salary.",
                    score=0.99,
                    metadata={"allowed_roles": ["admin"]},
                )
            ]
            return result

        mp.setattr("api.routes.ask.retrieve", fake_retrieve)
        mp.setattr("api.routes.ask.generate_answer", lambda *a, **k: mock_generated)
        mp.setattr(
            "api.routes.ask.cached_ask",
            lambda q, fn, **k: (
                fn(q),
                CacheMeta(cache="MISS", latency_ms=1.0),
            ),
        )
        client = TestClient(app)
        response = client.post(
            "/ask",
            json={"query": "admin salary policy", "user_role": "support"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["answer"] == NO_INFO_ANSWER
    assert body["citations"] == []


def test_ask_endpoint_admin_role_can_see_admin_chunks():
    from fastapi.testclient import TestClient

    import pytest

    from api.main import app
    from cache.middleware import CacheMeta
    from generation.citations import RawCitation

    admin_chunk = MagicMock()
    admin_chunk.id = "admin1"
    admin_chunk.doc_id = "doc-admin"
    admin_chunk.source = "internal-admin.md"
    admin_chunk.chunk_index = 0
    admin_chunk.text = "Junior support agents: **€38,000-€46,000** annual gross salary."
    admin_chunk.score = 0.99
    admin_chunk.metadata = {"allowed_roles": ["admin"]}

    mock_generated = MagicMock()
    mock_generated.query = "admin salary policy"
    mock_generated.answer = "Junior support agents are paid **€38,000-€46,000** gross annually."
    mock_generated.citations = [
        RawCitation(
            chunk_id="admin1",
            source="internal-admin.md",
            quote="Junior support agents: **€38,000-€46,000** annual gross salary.",
        )
    ]

    with pytest.MonkeyPatch.context() as mp:
        def fake_retrieve(query, *, user_role="support", **kwargs):
            result = MagicMock()
            result.query = query
            result.chunks = [admin_chunk] if user_role == "admin" else []
            return result

        mp.setattr("api.routes.ask.retrieve", fake_retrieve)
        mp.setattr("api.routes.ask.generate_answer", lambda *a, **k: mock_generated)
        mp.setattr(
            "api.routes.ask.cached_ask",
            lambda q, fn, **k: (
                fn(q),
                CacheMeta(cache="MISS", latency_ms=1.0),
            ),
        )
        client = TestClient(app)
        response = client.post(
            "/ask",
            json={"query": "admin salary policy", "user_role": "admin"},
        )

    assert response.status_code == 200
    body = response.json()
    assert "€38,000-€46,000" in body["answer"]
    assert body["citations"][0]["source"] == "internal-admin.md"
