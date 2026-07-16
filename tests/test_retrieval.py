from unittest.mock import MagicMock

from retrieval.fusion import reciprocal_rank_fusion
from retrieval.pipeline import retrieve
from retrieval.rerank import rerank_chunks
from retrieval.types import ScoredChunk


def _chunk(chunk_id: str, *, vector: float | None = None, keyword: float | None = None) -> ScoredChunk:
    return ScoredChunk(
        id=chunk_id,
        doc_id="doc-1",
        source="faq.md",
        chunk_index=0,
        text=f"text-{chunk_id}",
        vector_score=vector,
        keyword_score=keyword,
        score=0.0,
    )


def test_rrf_prefers_items_ranked_high_in_both_lists():
    keyword = [_chunk("a"), _chunk("b"), _chunk("c")]
    vector = [_chunk("b"), _chunk("a"), _chunk("d")]
    fused = reciprocal_rank_fusion(keyword, vector, k=60)
    assert fused[0].id == "a" or fused[0].id == "b"
    assert {c.id for c in fused} == {"a", "b", "c", "d"}
    assert all(c.rrf_score is not None and c.rrf_score > 0 for c in fused)


def test_rerank_boosts_high_vector_and_keyword():
    chunks = [
        _chunk("weak", vector=0.1, keyword=0.1),
        _chunk("strong", vector=0.9, keyword=0.8),
    ]
    for i, c in enumerate(chunks):
        c.rrf_score = 0.01 * (i + 1)
    ranked = rerank_chunks(chunks)
    assert ranked[0].id == "strong"


def test_retrieve_pipeline_with_mocks(monkeypatch):
    keyword_hits = [_chunk("k1", keyword=0.5)]
    vector_hits = [_chunk("v1", vector=0.9), _chunk("k1", vector=0.7)]
    keyword_hits[0].metadata = {"allowed_roles": ["support", "admin"]}
    vector_hits[0].metadata = {"allowed_roles": ["admin"]}
    vector_hits[1].metadata = {"allowed_roles": ["support", "admin"]}

    monkeypatch.setattr("retrieval.pipeline.run_migrations", lambda _url: None)
    monkeypatch.setattr("retrieval.pipeline.keyword_search", lambda *a, **k: keyword_hits)
    monkeypatch.setattr("retrieval.pipeline.vector_search", lambda *a, **k: vector_hits)

    from api.config import Settings

    cfg = Settings(
        openai_api_key="test",
        database_url="postgresql://copilot:copilot@localhost:5433/copilot",
        retrieve_top_k=2,
        retrieve_candidate_limit=10,
    )
    result = retrieve(
        "reset password",
        settings=cfg,
        embed_fn=lambda texts, settings=None: [[0.1] * 1536],
    )
    assert result.query == "reset password"
    assert len(result.chunks) <= 2
    assert all(c.score > 0 for c in result.chunks)
    assert all("support" in c.metadata["allowed_roles"] for c in result.chunks)


def test_retrieve_pipeline_filters_admin_only_chunks_for_support(monkeypatch):
    support_chunk = _chunk("support", vector=0.8, keyword=0.7)
    support_chunk.metadata = {"allowed_roles": ["support", "admin"]}
    admin_chunk = _chunk("admin", vector=0.95, keyword=0.9)
    admin_chunk.metadata = {"allowed_roles": ["admin"]}

    monkeypatch.setattr("retrieval.pipeline.run_migrations", lambda _url: None)
    monkeypatch.setattr("retrieval.pipeline.keyword_search", lambda *a, **k: [support_chunk, admin_chunk])
    monkeypatch.setattr("retrieval.pipeline.vector_search", lambda *a, **k: [admin_chunk, support_chunk])

    from api.config import Settings

    cfg = Settings(
        openai_api_key="test",
        database_url="postgresql://copilot:copilot@localhost:5433/copilot",
        retrieve_top_k=2,
        retrieve_candidate_limit=10,
    )
    result = retrieve(
        "admin salary policy",
        user_role="support",
        settings=cfg,
        embed_fn=lambda texts, settings=None: [[0.1] * 1536],
    )

    assert [c.id for c in result.chunks] == ["support"]


def test_retrieve_endpoint():
    from fastapi.testclient import TestClient

    from api.main import app

    mock_chunk = MagicMock()
    mock_chunk.id = "c1"
    mock_chunk.doc_id = "d1"
    mock_chunk.source = "faq.md"
    mock_chunk.chunk_index = 0
    mock_chunk.text = "Reset password via email."
    mock_chunk.score = 0.91
    mock_chunk.metadata = {"source": "faq.md"}

    mock_result = MagicMock()
    mock_result.query = "how to reset password"
    mock_result.chunks = [mock_chunk]

    import pytest

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("api.routes.retrieve.retrieve", lambda *a, **k: mock_result)
        client = TestClient(app)
        response = client.post(
            "/retrieve",
            json={"query": "how to reset password", "top_k": 3},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "how to reset password"
    assert body["chunks"][0]["source"] == "faq.md"
    assert body["chunks"][0]["text"].startswith("Reset password")


def test_retrieve_endpoint_passes_user_role():
    from fastapi.testclient import TestClient

    import pytest

    from api.main import app

    mock_result = MagicMock()
    mock_result.query = "admin salary policy"
    mock_result.chunks = []
    calls: list[str] = []

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(
            "api.routes.retrieve.retrieve",
            lambda *a, **k: calls.append(k["user_role"]) or mock_result,
        )
        client = TestClient(app)
        response = client.post(
            "/retrieve",
            json={"query": "admin salary policy", "user_role": "admin"},
        )

    assert response.status_code == 200
    assert calls == ["admin"]
