import json
from unittest.mock import MagicMock

from generation.citations import RawCitation, validate_citations
from generation.generator import generate_answer
from generation.prompt import NO_INFO_ANSWER, build_messages
from retrieval.types import ScoredChunk


def _chunk(
    chunk_id: str = "c1",
    *,
    text: str = "Customers may request a full refund within **30 days** of purchase.",
    source: str = "policies.md",
) -> ScoredChunk:
    return ScoredChunk(
        id=chunk_id,
        doc_id="d1",
        source=source,
        chunk_index=0,
        text=text,
        score=0.95,
    )


def test_build_messages_includes_chunk_ids():
    chunk = _chunk()
    messages = build_messages("What is the refund policy?", [chunk])
    assert messages[0]["role"] == "system"
    user = messages[1]["content"]
    assert "chunk_id=c1" in user
    assert "30 days" in user
    assert "What is the refund policy?" in user


def test_validate_citations_accepts_exact_substring():
    chunk = _chunk()
    citations = [
        RawCitation(
            chunk_id="c1",
            source="policies.md",
            quote="full refund within **30 days**",
        )
    ]
    valid = validate_citations("Refund within 30 days.", citations, [chunk])
    assert len(valid) == 1
    assert valid[0].quote.startswith("full refund")


def test_validate_citations_rejects_unknown_chunk():
    chunk = _chunk()
    citations = [RawCitation(chunk_id="missing", source="policies.md", quote="30 days")]
    valid = validate_citations("Refund within 30 days.", citations, [chunk])
    assert valid == []


def test_validate_citations_allows_empty_for_no_info_answer():
    valid = validate_citations(NO_INFO_ANSWER, [], [_chunk()])
    assert valid == []


def test_validate_citations_salvages_valid_sentences_from_gap_quote():
    chunk = _chunk(
        text=(
            "Customers may request a full refund within **30 days** of purchase if the product "
            "has not been substantially used. Partial refunds may apply when more than 50% of "
            "included usage quotas have been consumed."
        ),
    )
    citations = [
        RawCitation(
            chunk_id="c1",
            source="policies.md",
            quote=(
                "Customers may request a full refund within **30 days** of purchase if the product "
                "has not been substantially used. Made-up middle sentence. "
                "Partial refunds may apply when more than 50% of included usage quotas have been consumed."
            ),
        )
    ]
    valid = validate_citations("Refund policy summary.", citations, [chunk])
    assert len(valid) == 2
    assert valid[0].quote.startswith("Customers may request")
    assert "50%" in valid[1].quote


def test_generate_answer_with_mock_client():
    chunk = _chunk()
    mock_client = MagicMock()
    mock_response = MagicMock()
    mock_response.choices = [MagicMock()]
    mock_response.choices[0].message.content = json.dumps(
        {
            "answer": "Customers can request a refund within 30 days of purchase.",
            "citations": [
                {
                    "chunk_id": "c1",
                    "source": "policies.md",
                    "quote": "full refund within **30 days** of purchase",
                }
            ],
        }
    )
    mock_client.chat.completions.create.return_value = mock_response

    from api.config import Settings

    cfg = Settings(openai_api_key="test-key")
    result = generate_answer(
        "What is the refund policy?",
        [chunk],
        settings=cfg,
        client=mock_client,
    )
    assert "30 days" in result.answer
    assert len(result.citations) == 1
    assert result.citations[0].source == "policies.md"


def test_ask_endpoint():
    from fastapi.testclient import TestClient

    import pytest

    from api.main import app

    chunk = _chunk()
    mock_retrieved = MagicMock()
    mock_retrieved.chunks = [chunk]

    mock_generated = MagicMock()
    mock_generated.query = "What is the refund policy?"
    mock_generated.answer = "Refunds are available within 30 days."
    mock_generated.citations = [
        RawCitation(
            chunk_id="c1",
            source="policies.md",
            quote="full refund within **30 days**",
        )
    ]

    with pytest.MonkeyPatch.context() as mp:
        mp.setattr("api.routes.ask.retrieve", lambda *a, **k: mock_retrieved)
        mp.setattr("api.routes.ask.generate_answer", lambda *a, **k: mock_generated)
        client = TestClient(app)
        response = client.post(
            "/ask",
            json={"query": "What is the refund policy?"},
        )

    assert response.status_code == 200
    body = response.json()
    assert body["query"] == "What is the refund policy?"
    assert "30 days" in body["answer"]
    assert body["citations"][0]["source"] == "policies.md"
    assert "30 days" in body["citations"][0]["quote"]
