"""Compare RAGAS baseline metrics against configurable regression thresholds."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

import yaml

from eval.scorecard import METRIC_KEYS

EVAL_DIR = Path(__file__).resolve().parent
DEFAULT_BASELINE = EVAL_DIR / "baseline.json"
DEFAULT_THRESHOLDS = EVAL_DIR / "thresholds.yaml"

ENV_OVERRIDES = {
    "faithfulness": "REGRESSION_MIN_FAITHFULNESS",
    "answer_relevancy": "REGRESSION_MIN_ANSWER_RELEVANCY",
    "context_precision": "REGRESSION_MIN_CONTEXT_PRECISION",
    "context_recall": "REGRESSION_MIN_CONTEXT_RECALL",
}


def load_baseline(path: Path = DEFAULT_BASELINE) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(
            f"Baseline not found: {path}. Run `uv run python -m eval.ragas_run` first."
        )
    data = json.loads(path.read_text(encoding="utf-8"))
    metrics = data.get("metrics")
    if not isinstance(metrics, dict):
        raise ValueError(f"Invalid baseline (missing metrics): {path}")
    return data


def load_thresholds(path: Path = DEFAULT_THRESHOLDS) -> dict[str, Any]:
    if not path.exists():
        raise FileNotFoundError(f"Thresholds not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(raw, dict):
        raise ValueError(f"Invalid thresholds YAML: {path}")
    return raw


def effective_thresholds(raw: dict[str, Any]) -> dict[str, float]:
    """Merge YAML thresholds with REGRESSION_MIN_* environment overrides."""
    result: dict[str, float] = {}
    for key in METRIC_KEYS:
        if key not in raw or raw[key] is None:
            continue
        env_name = ENV_OVERRIDES[key]
        if env_name in os.environ and os.environ[env_name].strip():
            result[key] = float(os.environ[env_name])
        else:
            result[key] = float(raw[key])
    return result


def compare_metrics(
    metrics: dict[str, Any],
    thresholds: dict[str, float],
) -> list[str]:
    """Return human-readable failure lines (empty list = PASS)."""
    failures: list[str] = []
    for key, minimum in thresholds.items():
        value = metrics.get(key)
        if value is None:
            failures.append(f"{key}: missing in baseline (required >= {minimum:.2f})")
            continue
        score = float(value)
        if score < minimum:
            failures.append(f"{key}: {score:.4f} < {minimum:.2f}")
    return failures


def run_regression(
    *,
    baseline_path: Path = DEFAULT_BASELINE,
    thresholds_path: Path = DEFAULT_THRESHOLDS,
) -> tuple[bool, list[str], dict[str, float], dict[str, Any]]:
    baseline = load_baseline(baseline_path)
    thresholds = effective_thresholds(load_thresholds(thresholds_path))
    failures = compare_metrics(baseline.get("metrics", {}), thresholds)
    return (len(failures) == 0, failures, thresholds, baseline)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Gate on RAGAS baseline vs thresholds (exit 1 on regression)"
    )
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE)
    parser.add_argument("--thresholds", type=Path, default=DEFAULT_THRESHOLDS)
    args = parser.parse_args(argv)

    try:
        passed, failures, thresholds, baseline = run_regression(
            baseline_path=args.baseline,
            thresholds_path=args.thresholds,
        )
    except (FileNotFoundError, ValueError, OSError) as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        return 1

    metrics = baseline.get("metrics", {})
    print("Regression gate")
    print(f"  baseline: {args.baseline}")
    print(f"  samples:  {baseline.get('num_samples', '?')}")
    for key, minimum in thresholds.items():
        value = metrics.get(key)
        status = "ok" if value is not None and float(value) >= minimum else "FAIL"
        shown = "n/a" if value is None else f"{float(value):.4f}"
        print(f"  {key}: {shown} (min {minimum:.2f}) [{status}]")

    if passed:
        print("PASS: all metrics above threshold")
        return 0

    print("FAIL: metric regression detected", file=sys.stderr)
    for line in failures:
        print(f"  - {line}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
