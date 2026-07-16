from unittest.mock import MagicMock

import pytest

from api.config import Settings
from ingestion.chunker import chunk_text
from ingestion.pipeline import ingest_text


def test_chunk_text_splits_long_document():
    text = "word " * 400
    chunks = chunk_text(
        text,
        source="faq.md",
        doc_id="doc-1",
        chunk_size=512,
        overlap=64,
    )
    assert len(chunks) >= 2
    assert chunks[0].chunk_index == 0
    assert chunks[1].chunk_index == 1
    assert all(c.metadata["allowed_roles"] == ["support", "admin"] for c in chunks)


def test_chunk_text_empty_returns_empty_list():
    assert chunk_text("", source="x.md", doc_id="doc-1") == []


def test_chunk_text_overlap_invalid():
    with pytest.raises(ValueError):
        chunk_text("hello", source="x.md", doc_id="doc-1", chunk_size=100, overlap=100)


def test_ingest_text_with_mocked_embed_and_store(monkeypatch):
    saved_chunks = []

    def mock_embed(texts, *, settings=None, client=None):
        return [[0.01] * 1536 for _ in texts]

    def mock_save(chunks, *, database_url):
        saved_chunks.extend(chunks)
        return len(chunks)

    monkeypatch.setattr("ingestion.pipeline.run_migrations", lambda _url: None)
    monkeypatch.setattr("ingestion.pipeline.save_chunks", mock_save)
    monkeypatch.setattr("ingestion.pipeline.invalidate_cache", lambda **k: 0)

    cfg = Settings(
        openai_api_key="test-key",
        database_url="postgresql://copilot:copilot@localhost:5433/copilot",
        chunk_size=200,
        chunk_overlap=20,
    )
    body = "Support answer. " * 50
    result = ingest_text(
        body,
        source="faq.md",
        settings=cfg,
        embed_fn=mock_embed,
    )

    assert result.chunk_count == len(saved_chunks)
    assert result.source == "faq.md"
    assert all(c.embedding is not None for c in saved_chunks)


def test_ingest_endpoint_accepts_upload():
    from fastapi.testclient import TestClient

    from api.main import app

    mock_result = MagicMock()
    mock_result.doc_id = "doc-123"
    mock_result.source = "faq.md"
    mock_result.chunk_count = 3

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("api.routes.ingest.ingest_text", lambda *a, **k: mock_result)
        client = TestClient(app)
        response = client.post(
            "/ingest",
            files={"file": ("faq.md", b"# FAQ\n\nReset password via email.", "text/markdown")},
        )

    assert response.status_code == 200
    assert response.json() == {
        "doc_id": "doc-123",
        "source": "faq.md",
        "chunk_count": 3,
    }
