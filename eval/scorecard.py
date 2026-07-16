"""Format and persist RAGAS baseline metrics."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

BASELINE_PATH = Path(__file__).resolve().parent / "baseline.json"

METRIC_KEYS = (
    "faithfulness",
    "answer_relevancy",
    "context_precision",
    "context_recall",
)


def format_metrics(raw: Mapping[str, Any], *, num_samples: int) -> dict[str, Any]:
    """Normalize RAGAS result dict into a stable scorecard payload."""
    metrics: dict[str, float | None] = {}
    for key in METRIC_KEYS:
        value = raw.get(key)
        if value is None:
            metrics[key] = None
        else:
            metrics[key] = round(float(value), 4)

    return {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "num_samples": num_samples,
        "metrics": metrics,
    }


def write_baseline(scorecard: Mapping[str, Any], path: Path | None = None) -> Path:
    out = path or BASELINE_PATH
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(scorecard, indent=2) + "\n", encoding="utf-8")
    return out


def print_scorecard(scorecard: Mapping[str, Any]) -> None:
    metrics = scorecard.get("metrics", {})
    parts = []
    for key in METRIC_KEYS:
        value = metrics.get(key)
        label = key.replace("_", " ").title()
        if value is None:
            parts.append(f"{label}: n/a")
        else:
            parts.append(f"{label}: {value:.2f}")
    print(" | ".join(parts))
    print(f"Samples: {scorecard.get('num_samples', 0)}")
