"""Tests for golden dataset loading and scorecard formatting.

Full RAGAS + live /ask runs are skipped in CI when OPENAI_API_KEY is unset.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from eval.ragas_run import load_golden
from eval.scorecard import format_metrics, write_baseline

GOLDEN_PATH = Path(__file__).resolve().parents[1] / "eval" / "golden.jsonl"


def test_golden_dataset_schema_and_size():
    rows = load_golden(GOLDEN_PATH)
    assert 20 <= len(rows) <= 40
    categories = {r.get("category") for r in rows}
    assert "factual" in categories
    assert "policy" in categories
    assert "negative" in categories
    for row in rows:
        assert row["question"].strip()
        assert row["ground_truth"].strip()
        # Questions should not be verbatim FAQ headings pasted as the only content
        assert not row["question"].startswith("### ")


def test_format_and_write_baseline(tmp_path: Path):
    scorecard = format_metrics(
        {
            "faithfulness": 0.87123,
            "answer_relevancy": 0.82,
            "context_precision": 0.79,
            "context_recall": 0.75,
        },
        num_samples=25,
    )
    assert scorecard["num_samples"] == 25
    assert scorecard["metrics"]["faithfulness"] == 0.8712
    out = write_baseline(scorecard, path=tmp_path / "baseline.json")
    loaded = json.loads(out.read_text(encoding="utf-8"))
    assert loaded["metrics"]["answer_relevancy"] == 0.82


def test_load_golden_rejects_bad_line(tmp_path: Path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"question": "q"}\n', encoding="utf-8")
    with pytest.raises(ValueError, match="ground_truth"):
        load_golden(path)


@pytest.mark.skipif(
    not os.environ.get("OPENAI_API_KEY")
    or os.environ.get("OPENAI_API_KEY", "").startswith("sk-your-"),
    reason="OPENAI_API_KEY required for live RAGAS smoke",
)
@pytest.mark.skipif(
    os.environ.get("RUN_RAGAS_LIVE") != "1",
    reason="Set RUN_RAGAS_LIVE=1 to exercise live /ask + RAGAS (expensive)",
)
def test_ragas_run_smoke_live():
    from eval.ragas_run import main

    assert main(["--limit", "2"]) == 0


def test_ragas_run_collect_predictions_mocked():
    from eval.ragas_run import collect_predictions

    golden = [
        {
            "question": "What is the refund policy?",
            "ground_truth": "Refund within 30 days.",
        }
    ]

    ask_body = {"answer": "Refund within 30 days of purchase.", "citations": []}
    retrieve_body = {
        "chunks": [
            {"text": "Customers may request a full refund within 30 days of purchase."},
        ]
    }

    mock_response_ask = MagicMock()
    mock_response_ask.raise_for_status = MagicMock()
    mock_response_ask.json.return_value = ask_body

    mock_response_retrieve = MagicMock()
    mock_response_retrieve.raise_for_status = MagicMock()
    mock_response_retrieve.json.return_value = retrieve_body

    mock_health = MagicMock()
    mock_health.raise_for_status = MagicMock()

    mock_client = MagicMock()
    mock_client.__enter__.return_value = mock_client
    mock_client.__exit__.return_value = None
    mock_client.get.return_value = mock_health

    def post(url, json=None):  # noqa: A002
        if url.endswith("/ask"):
            return mock_response_ask
        if url.endswith("/retrieve"):
            return mock_response_retrieve
        raise AssertionError(url)

    mock_client.post.side_effect = post

    with patch("eval.ragas_run.httpx.Client", return_value=mock_client):
        result = collect_predictions(golden, base_url="http://test")

    assert result["user_input"] == ["What is the refund policy?"]
    assert "30 days" in result["response"][0]
    assert result["retrieved_contexts"][0][0].startswith("Customers may request")
    assert result["reference"] == ["Refund within 30 days."]
