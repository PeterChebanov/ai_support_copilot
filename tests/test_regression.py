"""Regression gate tests — threshold pass and simulated fail."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from eval.regression import (
    compare_metrics,
    effective_thresholds,
    load_baseline,
    load_thresholds,
    main,
    run_regression,
)

EVAL_DIR = Path(__file__).resolve().parents[1] / "eval"


def test_committed_baseline_passes_default_thresholds():
    passed, failures, thresholds, _ = run_regression()
    assert thresholds["faithfulness"] == 0.80
    assert passed, f"expected PASS, got failures: {failures}"


def test_compare_metrics_detects_drop():
    failures = compare_metrics(
        {"faithfulness": 0.50, "answer_relevancy": 0.90, "context_precision": 0.90},
        {"faithfulness": 0.80, "answer_relevancy": 0.50, "context_precision": 0.70},
    )
    assert any("faithfulness" in f for f in failures)
    assert len(failures) == 1


def test_env_override_forces_fail(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("REGRESSION_MIN_FAITHFULNESS", "0.99")
    raw = load_thresholds(EVAL_DIR / "thresholds.yaml")
    thresholds = effective_thresholds(raw)
    assert thresholds["faithfulness"] == 0.99
    baseline = load_baseline(EVAL_DIR / "baseline.json")
    failures = compare_metrics(baseline["metrics"], thresholds)
    assert any("faithfulness" in f for f in failures)


def test_cli_pass_and_fail(monkeypatch: pytest.MonkeyPatch):
    assert main([]) == 0
    monkeypatch.setenv("REGRESSION_MIN_FAITHFULNESS", "0.99")
    assert main([]) == 1


def test_load_baseline_requires_metrics(tmp_path: Path):
    path = tmp_path / "bad.json"
    path.write_text(json.dumps({"num_samples": 1}), encoding="utf-8")
    with pytest.raises(ValueError, match="metrics"):
        load_baseline(path)


def test_citation_required_flag_in_thresholds():
    raw = load_thresholds(EVAL_DIR / "thresholds.yaml")
    assert raw.get("citation_required") is True
