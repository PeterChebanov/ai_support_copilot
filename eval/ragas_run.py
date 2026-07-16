"""Run RAGAS evaluation against the live /ask + /retrieve API."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import httpx
from datasets import Dataset
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
from ragas import evaluate
from ragas.embeddings import LangchainEmbeddingsWrapper
from ragas.llms import LangchainLLMWrapper
from ragas.metrics import (
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from eval.scorecard import format_metrics, print_scorecard, write_baseline

GOLDEN_PATH = Path(__file__).resolve().parent / "golden.jsonl"
DEFAULT_BASE_URL = "http://localhost:8000"
DEFAULT_TIMEOUT = 120.0


def load_golden(path: Path = GOLDEN_PATH) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        text = line.strip()
        if not text:
            continue
        try:
            row = json.loads(text)
        except json.JSONDecodeError as exc:
            raise ValueError(f"Invalid JSONL at {path}:{line_no}") from exc
        for required in ("question", "ground_truth"):
            if required not in row or not str(row[required]).strip():
                raise ValueError(f"Missing {required!r} at {path}:{line_no}")
        rows.append(row)
    if not rows:
        raise ValueError(f"No samples found in {path}")
    return rows


def _ask(client: httpx.Client, base_url: str, question: str) -> str:
    response = client.post(f"{base_url}/ask", json={"query": question})
    response.raise_for_status()
    body = response.json()
    answer = body.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        raise RuntimeError(f"/ask returned empty answer for: {question!r}")
    return answer


def _retrieve_contexts(client: httpx.Client, base_url: str, question: str) -> list[str]:
    response = client.post(
        f"{base_url}/retrieve",
        json={"query": question, "top_k": 5},
    )
    response.raise_for_status()
    chunks = response.json().get("chunks") or []
    return [c["text"] for c in chunks if isinstance(c.get("text"), str) and c["text"].strip()]


def collect_predictions(
    golden: list[dict[str, Any]],
    *,
    base_url: str = DEFAULT_BASE_URL,
    timeout: float = DEFAULT_TIMEOUT,
    limit: int | None = None,
) -> dict[str, list[Any]]:
    samples = golden if limit is None else golden[:limit]
    questions: list[str] = []
    answers: list[str] = []
    contexts: list[list[str]] = []
    references: list[str] = []

    with httpx.Client(timeout=timeout) as client:
        # Fail fast if the API is down
        health = client.get(f"{base_url}/health")
        health.raise_for_status()

        for i, row in enumerate(samples, start=1):
            question = row["question"]
            print(f"[{i}/{len(samples)}] {question}", flush=True)
            answer = _ask(client, base_url, question)
            retrieved = _retrieve_contexts(client, base_url, question)
            questions.append(question)
            answers.append(answer)
            contexts.append(retrieved)
            references.append(row["ground_truth"])

    return {
        "user_input": questions,
        "response": answers,
        "retrieved_contexts": contexts,
        "reference": references,
    }


def run_ragas(dataset_dict: dict[str, list[Any]], *, model: str | None = None) -> dict[str, Any]:
    api_key = os.environ.get("OPENAI_API_KEY", "").strip()
    if not api_key or api_key.startswith("sk-your-"):
        raise RuntimeError("OPENAI_API_KEY is required to run RAGAS (judge LLM + embeddings).")

    judge_model = model or os.environ.get("LLM_MODEL", "gpt-4o-mini")
    llm = LangchainLLMWrapper(ChatOpenAI(model=judge_model, temperature=0))
    embeddings = LangchainEmbeddingsWrapper(
        OpenAIEmbeddings(model=os.environ.get("EMBEDDING_MODEL", "text-embedding-3-small"))
    )

    dataset = Dataset.from_dict(dataset_dict)
    result = evaluate(
        dataset,
        metrics=[
            faithfulness,
            answer_relevancy,
            context_precision,
            context_recall,
        ],
        llm=llm,
        embeddings=embeddings,
    )
    # ragas Result supports dict-like access and .scores
    if hasattr(result, "_repr_dict"):
        return dict(result._repr_dict)
    return {k: result[k] for k in ("faithfulness", "answer_relevancy", "context_precision", "context_recall")}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Run RAGAS baseline against live /ask")
    parser.add_argument(
        "--base-url",
        default=os.environ.get("EVAL_BASE_URL", DEFAULT_BASE_URL),
        help="API base URL (default: http://localhost:8000)",
    )
    parser.add_argument(
        "--golden",
        type=Path,
        default=GOLDEN_PATH,
        help="Path to golden.jsonl",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Optional cap on number of golden samples (for smoke runs)",
    )
    parser.add_argument(
        "--skip-evaluate",
        action="store_true",
        help="Collect /ask answers only (no RAGAS judge calls)",
    )
    args = parser.parse_args(argv)

    # Load .env into process if present (local convenience)
    env_path = Path(__file__).resolve().parents[1] / ".env"
    if env_path.exists() and not os.environ.get("OPENAI_API_KEY"):
        for line in env_path.read_text(encoding="utf-8").splitlines():
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value

    golden = load_golden(args.golden)
    predictions = collect_predictions(
        golden,
        base_url=args.base_url.rstrip("/"),
        limit=args.limit,
    )

    if args.skip_evaluate:
        print(f"Collected {len(predictions['user_input'])} predictions (RAGAS skipped).")
        return 0

    raw = run_ragas(predictions)
    scorecard = format_metrics(raw, num_samples=len(predictions["user_input"]))
    print_scorecard(scorecard)
    out = write_baseline(scorecard)
    print(f"Saved to {out}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except Exception as exc:  # noqa: BLE001 — CLI entrypoint
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
